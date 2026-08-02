"""Notifier entrypoint; policy and workflow live in dedicated modules."""

import time

import pywikibot
import redis
from tqdm import tqdm

import config
from models import NominationCodec
from notifier_service import NotifierService
from transport import RedisMarkerTransport
from wikimedia import WikimediaGateway


def build_service(site=None, redis_client=None, clock=time.time):
    site = site or pywikibot.Site()
    redis_client = redis_client or redis.Redis(
        host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB
    )
    transport = RedisMarkerTransport(
        redis_client, config.REDIS_PREFIX, config.EXPIREMINS, config.PUBFILEDIR, clock
    )
    return NotifierService(transport, NominationCodec(config.KEY), WikimediaGateway(site))


def main(*args):
    pywikibot.handle_args(*args)
    site = pywikibot.Site()
    if not site.logged_in():
        site.login()
    return build_service(site).process_once()


if __name__ == "__main__":
    count = 0
    while True:
        try:
            main()
            count += 1
            if count % 20 == 0:
                print("Stopping and restarting")
                raise SystemExit
            print("\n\nSLEEP FOR '5 minutes'")
            for _ in tqdm(range(5)):
                time.sleep(60)
        except SystemExit:
            raise
        except Exception as err:
            print(err)
