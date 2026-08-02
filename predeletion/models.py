"""Stable records exchanged between the publisher and notifier."""

from pywikibot.tools import strtobool

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Mapping

from cryptography.fernet import Fernet


WIRE_FIELDS = (
    "file_name",
    "nominator",
    "uploader",
    "uploader_is_nominator",
    "deletion_category",
    "is_a_moved_file_redirect",
    "nomination_time",
    "latest_revision_time",
    "latest_revision_sha1",
    "nomination_reason",
)


@dataclass(frozen=True, kw_only=True)
class DeletionNomination:
    file_name: str
    nominator: str
    uploader: str
    uploader_is_nominator: bool
    deletion_category: str
    is_a_moved_file_redirect: bool
    nomination_time: str
    latest_revision_time: str
    latest_revision_sha1: str
    nomination_reason: str
    marker_path: Path | None = None

    @property
    def category_hash(self) -> str:
        return hashlib.md5(self.deletion_category.encode("utf-8")).hexdigest()

    @property
    def redis_key(self) -> str:
        return f"{self.category_hash}_{self.latest_revision_sha1}"

    def with_marker(self, path: Path) -> "DeletionNomination":
        return replace(self, marker_path=path)


class NominationCodec:
    """Compatibility codec: each legacy wire field is independently encrypted."""

    def __init__(self, key: str):
        self._cipher = Fernet(key.encode())

    def encode(self, nomination: DeletionNomination) -> dict[str, str]:
        return {
            field: self._cipher.encrypt(
                str(getattr(nomination, field)).strip().encode()
            ).decode()
            for field in WIRE_FIELDS
        }

    def decode(self, value: Mapping[str, str]) -> DeletionNomination:
        return DeletionNomination(
            file_name=self._decrypt_field(value, "file_name"),
            nominator=self._decrypt_field(value, "nominator"),
            uploader=self._decrypt_field(value, "uploader"),
            uploader_is_nominator=strtobool(
                self._decrypt_field(value, "uploader_is_nominator")
            ),
            deletion_category=self._decrypt_field(value, "deletion_category"),
            is_a_moved_file_redirect=strtobool(
                self._decrypt_field(value, "is_a_moved_file_redirect")
            ),
            nomination_time=self._decrypt_field(value, "nomination_time"),
            latest_revision_time=self._decrypt_field(value, "latest_revision_time"),
            latest_revision_sha1=self._decrypt_field(value, "latest_revision_sha1"),
            nomination_reason=self._decrypt_field(value, "nomination_reason"),
        )

    def _decrypt_field(self, value: Mapping[str, str], field: str) -> str:
        return self._cipher.decrypt(value[field].encode()).decode()


def marker_name(timestamp: int | str, redis_key: str) -> str:
    """Return the existing ``<unix>_<category-md5>_<sha1>`` marker name."""
    return f"{timestamp}_{redis_key}"
