import redis

from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PREFIX,
    EXPIREMINS,
    PUBFILEDIR,
)


from transport import RedisMarkerTransport

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
transport = RedisMarkerTransport(r, REDIS_PREFIX, EXPIREMINS, PUBFILEDIR)


def setex(key, value):
    return transport.publish(key, value)


def get(key):
    return transport.get(key)


if __name__ == "__main__":
    setex("key", "this value is stored and should be printed if this script is run")
    print(get("key"))
