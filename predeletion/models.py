"""Stable records exchanged between the publisher and notifier."""

from dataclasses import dataclass
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


@dataclass(frozen=True)
class DeletionNomination:
    file_name: str
    nominator: str
    uploader: str
    uploader_is_nominator: str
    deletion_category: str
    is_a_moved_file_redirect: str
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
        return DeletionNomination(**{**self.__dict__, "marker_path": path})


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
        data = {
            field: self._cipher.decrypt(value[field].encode()).decode()
            for field in WIRE_FIELDS
        }
        return DeletionNomination(**data)


def marker_name(timestamp: int | str, redis_key: str) -> str:
    """Return the existing ``<unix>_<category-md5>_<sha1>`` marker name."""
    return f"{timestamp}_{redis_key}"
