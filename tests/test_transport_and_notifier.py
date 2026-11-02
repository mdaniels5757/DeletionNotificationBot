from datetime import date
from dataclasses import replace
from cryptography.fernet import Fernet
import pytest

from models import DeletionNomination, NominationCodec
from notifier_service import NotifierService
from transport import RedisMarkerTransport
from preferences import NotificationPreferences


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key, "").encode() or None


class FakeWiki:
    def __init__(self):
        self.submissions = []
        self.ineligible = set()
        self.preferences = NotificationPreferences()
        self.preference_calls = []
        self.redirects = set()
        self.redirect_error = False

    def notification_preferences(self, uploader):
        self.preference_calls.append(uploader)
        return self.preferences

    def is_redirect(self, item):
        if self.redirect_error:
            raise RuntimeError("wiki unavailable")
        return item.file_name in self.redirects

    def is_notifiable(self, item, _):
        return item.file_name not in self.ineligible

    def submit(self, uploader, notice, summary):
        self.submissions.append((uploader, notice, summary))


def record(name="File:One.jpg", sha1="a" * 40):
    return DeletionNomination(
        file_name=name,
        nominator="Nom",
        uploader="Up",
        uploader_is_nominator=False,
        deletion_category="Copyright violations",
        is_a_moved_file_redirect=False,
        nomination_time="n",
        latest_revision_time="l",
        latest_revision_sha1=sha1,
        nomination_reason="Reason",
    )


def test_transport_and_notifier_acknowledge_only_processed_markers(tmp_path):
    now = 10_000
    redis = FakeRedis()
    clock = [now - 601]
    transport = RedisMarkerTransport(
        redis, "prefix:", 60, tmp_path, clock=lambda: clock[0]
    )
    codec = NominationCodec(Fernet.generate_key().decode())
    first, second = record(), record("File:Two.jpg", "b" * 40)
    first_marker = transport.publish(first.redis_key, codec.encode(first))
    second_marker = transport.publish(second.redis_key, codec.encode(second))
    clock[0] = now
    wiki = FakeWiki()
    service = NotifierService(transport, codec, wiki, today=lambda: date(2026, 8, 2))

    assert service.process_once() == 1
    assert len(wiki.submissions) == 1
    assert not first_marker.exists()
    assert not second_marker.exists()


def test_expired_value_leaves_marker_for_pruner(tmp_path):
    transport = RedisMarkerTransport(
        FakeRedis(), "p:", 60, tmp_path, clock=lambda: 10_000
    )
    marker = tmp_path / ("9000_" + "a" * 32 + "_" + "b" * 40)
    marker.touch()
    service = NotifierService(
        transport,
        NominationCodec(Fernet.generate_key().decode()),
        FakeWiki(),
        today=lambda: date(2026, 8, 2),
    )
    assert service.process_once() == 0
    assert marker.exists()


def setup_group(tmp_path, items, wiki):
    clock = [9000]
    transport = RedisMarkerTransport(
        FakeRedis(), "p:", 60, tmp_path, clock=lambda: clock[0]
    )
    codec = NominationCodec(Fernet.generate_key().decode())
    markers = [transport.publish(item.redis_key, codec.encode(item)) for item in items]
    clock[0] = 10000
    service = NotifierService(transport, codec, wiki, today=lambda: date(2026, 8, 2))
    return service, markers


@pytest.mark.parametrize("redirect_first", [True, False])
def test_redirects_filtered_from_notice_and_summary(tmp_path, redirect_first):
    wiki = FakeWiki()
    wiki.preferences = NotificationPreferences(notify_redirects=False)
    redirect = record("File:Redirect.jpg", "a" * 40)
    normal = record("File:Normal.jpg", "b" * 40)
    wiki.redirects.add(redirect.file_name)
    service, markers = setup_group(
        tmp_path, [redirect, normal] if redirect_first else [normal, redirect], wiki
    )
    assert service.process_once() == 1
    _, notice, summary = wiki.submissions[0]
    assert "File:Normal.jpg" in notice and "File:Normal.jpg" in summary
    assert "File:Redirect.jpg" not in notice + summary
    assert "And also:" not in notice
    assert all(not marker.exists() for marker in markers)


def test_all_redirects_are_acknowledged_without_notification(tmp_path):
    wiki = FakeWiki()
    wiki.preferences = NotificationPreferences(notify_redirects=False)
    wiki.redirects.add("File:One.jpg")
    service, markers = setup_group(tmp_path, [record()], wiki)
    assert service.process_once() == 0
    assert not wiki.submissions and not markers[0].exists()


def test_opt_out_acknowledges_all_categories_and_reads_once(tmp_path):
    wiki = FakeWiki()
    wiki.preferences = NotificationPreferences(notifications=False, notify_redirects=False)
    items = [record(), replace(record("File:Two.jpg", "b" * 40), deletion_category="Other speedy deletions")]
    service, markers = setup_group(tmp_path, items, wiki)
    assert service.process_once() == 0
    assert wiki.preference_calls == ["Up"]
    assert not wiki.submissions and all(not marker.exists() for marker in markers)


def test_redirect_error_retries_eligible_items(tmp_path):
    wiki = FakeWiki()
    wiki.preferences = NotificationPreferences(notify_redirects=False)
    wiki.redirect_error = True
    wiki.ineligible.add("File:Two.jpg")
    service, markers = setup_group(tmp_path, [record(), record("File:Two.jpg", "b" * 40)], wiki)
    assert service.process_once() == 0
    assert not wiki.submissions
    assert markers[0].exists() and not markers[1].exists()


def test_submission_failure_keeps_non_redirect_marker(tmp_path):
    wiki = FakeWiki()
    wiki.preferences = NotificationPreferences(notify_redirects=False)
    wiki.redirects.add("File:One.jpg")

    def fail_submit(*args):
        raise RuntimeError("edit failed")

    wiki.submit = fail_submit
    service, markers = setup_group(
        tmp_path, [record(), record("File:Two.jpg", "b" * 40)], wiki
    )
    with pytest.raises(RuntimeError, match="edit failed"):
        service.process_once()
    assert not markers[0].exists() and markers[1].exists()


def test_defaults_do_not_check_redirects(tmp_path):
    wiki = FakeWiki()
    wiki.redirect_error = True
    service, markers = setup_group(tmp_path, [record()], wiki)
    assert service.process_once() == 1
    assert not markers[0].exists()
