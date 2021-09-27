import redis
from datetime import timedelta
import time
import json

from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PREFIX,
    EXPIREMINS,
    PUBFILEDIR,
)


r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


def setex(key, value):
    secure_key = REDIS_PREFIX + key
    json_dumps_value = json.dumps(value)
    r.setex(secure_key, timedelta(minutes=EXPIREMINS), json_dumps_value)
    file_name = PUBFILEDIR + str(int(time.time())) + "_" + key
    open(file_name, "a").close()


def get(key):
    secure_key = REDIS_PREFIX + key
    value = r.get(secure_key)
    if not value:
        return None
    return json.loads(value.decode())


if __name__ == "__main__":
    setex("key", "this value is stored and should be printed if this script is run")
    print(get("key"))
