from cryptography.fernet import Fernet

from models import DeletionNomination, NominationCodec, marker_name


def nomination():
    return DeletionNomination(
        "File:Example.jpg",
        "Nominator",
        "Uploader",
        "False",
        "Copyright violations",
        "False",
        "2026-01-01",
        "2026-01-02",
        "a" * 40,
        "A reason",
    )


def test_legacy_wire_codec_round_trip_and_key_shape():
    item = nomination()
    codec = NominationCodec(Fernet.generate_key().decode())
    encoded = codec.encode(item)

    assert set(encoded) == {
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
    }
    assert codec.decode(encoded) == item
    assert item.redis_key.endswith("_" + "a" * 40)
    assert marker_name(123, item.redis_key).startswith("123_")
