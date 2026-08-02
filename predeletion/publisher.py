"""Publisher compatibility facade and composition root."""

from datetime import datetime, timezone

import pywikibot
import redis

import config
from models import NominationCodec
from transport import RedisMarkerTransport
from wikimedia import WikimediaGateway


class FileNominatedForDeletion:
    """Legacy public facade for publishing one nominated file."""

    def __init__(self, file_name: str, site: pywikibot.site.BaseSite | None = None):
        self.file_name = file_name
        self.site = site or pywikibot.Site()
        self._gateway = WikimediaGateway(self.site)
        nomination = self._gateway.build_nomination(
            file_name, datetime.now(tz=timezone.utc).date()
        )
        if nomination is None:
            raise ValueError("%s is not in a supported deletion category" % file_name)
        self.nomination = nomination
        for field in nomination.__dataclass_fields__:
            setattr(
                self,
                field if field != "uploader" else "_uploader",
                getattr(nomination, field),
            )
        self.category_md5_hash = nomination.category_hash

    def uploader(self, link=False, obj=False):
        # Kept for callers of the former class API; publication itself uses the record.
        page = pywikibot.Page(self.site, self.file_name)
        from utils import page_creator

        return page_creator(page, link=link, obj=obj)

    def publish(self, transport=None, codec=None):
        transport = transport or build_transport()
        codec = codec or NominationCodec(config.KEY)
        return transport.publish(
            self.nomination.redis_key, codec.encode(self.nomination)
        )

    def __repr__(self):
        values = self.nomination
        return (
            "\n-----\n FileName : %s\n Nominator : %s\n Uploader : %s\n Category : %s\n CategoryMD5Hash : %s\n MovedFileRedirect : %s\n NominationTime : %s\n LastRevisionTime : %s\n LastRevisionSha1 : %s\n Reason : %s\n-----"
            % (
                values.file_name,
                values.nominator,
                values.uploader,
                values.deletion_category,
                values.category_hash,
                values.is_a_moved_file_redirect,
                values.nomination_time,
                values.latest_revision_time,
                values.latest_revision_sha1,
                values.nomination_reason,
            )
        )


def build_transport():
    client = redis.Redis(
        host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB
    )
    return RedisMarkerTransport(
        client, config.REDIS_PREFIX, config.EXPIREMINS, config.PUBFILEDIR
    )


def main():
    # Retains the historical manual single-file smoke entry point.
    nomination = FileNominatedForDeletion("File:Gaime.play.jpg")
    print(repr(nomination))
    nomination.publish()


if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
