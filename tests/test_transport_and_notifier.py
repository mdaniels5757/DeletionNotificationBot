from datetime import date
from cryptography.fernet import Fernet

from models import DeletionNomination, NominationCodec
from notifier_service import NotifierService
from transport import RedisMarkerTransport


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

    def is_notifiable(self, item, _):
        return item.file_name not in self.ineligible

    def submit(self, uploader, notice, summary):
        self.submissions.append((uploader, notice, summary))


def record(name="File:One.jpg", sha1="a" * 40):
    return DeletionNomination(
        name,
        "Nom",
        "Up",
        "False",
        "Copyright violations",
        "False",
        "n",
        "l",
        sha1,
        "Reason",
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
