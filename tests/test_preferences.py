import pytest
import pywikibot

from preferences import NotificationPreferences
from wikimedia import WikimediaGateway


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{}', NotificationPreferences()),
        ('{"notifications": false}', NotificationPreferences(notifications=False)),
        ('{"notify_redirects": false}', NotificationPreferences(notify_redirects=False)),
        ('{"notifications": false, "notify_redirects": false}', NotificationPreferences(False, False)),
    ],
)
def test_parse_preferences(text, expected):
    assert NotificationPreferences.from_json(text) == expected


@pytest.mark.parametrize("text", ['{', '[]', 'null', '{"notifications": 0}', '{"notify_redirects": "false"}', '{"unknown": true}', '{"notifications": false, "unknown": true}'])
def test_invalid_preferences(text):
    with pytest.raises(ValueError):
        NotificationPreferences.from_json(text)


def test_gateway_reads_user_configuration(monkeypatch):
    titles = []

    class Page:
        def __init__(self, site, title):
            titles.append(title)

        def get(self):
            return '{"notify_redirects": false}'

    monkeypatch.setattr(pywikibot, "Page", Page)
    assert not WikimediaGateway(object()).notification_preferences("Example").notify_redirects
    assert titles == ["User:Example/Deletion Notification Bot.json"]


@pytest.mark.parametrize("failure", ["missing", "unreadable", "invalid"])
def test_gateway_defaults_on_missing_or_invalid_configuration(monkeypatch, caplog, failure):
    warnings = []
    class Page:
        def __init__(self, site, title):
            pass

        def get(self):
            if failure == "missing":
                raise pywikibot.exceptions.NoPageError(self)
            if failure == "unreadable":
                raise RuntimeError("unavailable")
            return '{"notifications": "false"}'

    monkeypatch.setattr(pywikibot, "Page", Page)
    monkeypatch.setattr(
        WikimediaGateway, "_warn_invalid_preferences",
        lambda self, uploader, text: warnings.append((uploader, text)),
    )
    assert WikimediaGateway(object()).notification_preferences("Example") == NotificationPreferences()
    assert bool(caplog.records) == (failure != "missing")
    assert bool(warnings) == (failure == "invalid")


def test_invalid_config_warning_is_deduplicated_and_tracks_changes(monkeypatch):
    pages = {"User:Example/Deletion Notification Bot.json": "{"}
    writes = []

    class Page:
        def __init__(self, site, title):
            self.title = title

        def get(self):
            if self.title not in pages:
                raise pywikibot.exceptions.NoPageError(self)
            return pages[self.title]

        def isRedirectPage(self):
            return False

    def save(old_text, new_text, page, summary):
        writes.append((page.title, new_text, summary))
        pages[page.title] = new_text

    monkeypatch.setattr(pywikibot, "Page", Page)
    monkeypatch.setattr("wikimedia.commit", save)
    gateway = WikimediaGateway(object())
    gateway.notification_preferences("Example")
    gateway.notification_preferences("Example")
    assert len(writes) == 1
    assert writes[0][0] == "User talk:Example"
    assert "User:Example/Deletion Notification Bot.json" in writes[0][1]
    assert "default settings" in writes[0][1]
    pages["User:Example/Deletion Notification Bot.json"] = "[]"
    gateway.notification_preferences("Example")
    assert len(writes) == 2


def test_warning_failure_does_not_prevent_defaults(monkeypatch, caplog):
    class Page:
        def __init__(self, site, title):
            pass

        def get(self):
            return "{"

    def fail(*args):
        raise RuntimeError("edit failed")

    monkeypatch.setattr(pywikibot, "Page", Page)
    monkeypatch.setattr(WikimediaGateway, "_warn_invalid_preferences", fail)
    assert WikimediaGateway(object()).notification_preferences("Example") == NotificationPreferences()
    assert "Could not warn Example" in caplog.text
