"""Redis plus marker-file compatibility transport."""

from datetime import timedelta
from pathlib import Path
import json
import time

from models import marker_name


class RedisMarkerTransport:
    def __init__(
        self,
        redis_client,
        prefix: str,
        expire_minutes: int,
        marker_dir: str | Path,
        clock=time.time,
    ):
        self.redis = redis_client
        self.prefix = prefix
        self.expire_minutes = expire_minutes
        self.marker_dir = Path(marker_dir)
        self.clock = clock

    def publish(self, key: str, value: dict[str, str]) -> Path:
        self.redis.setex(
            self.prefix + key, timedelta(minutes=self.expire_minutes), json.dumps(value)
        )
        path = self.marker_dir / marker_name(int(self.clock()), key)
        path.touch(exist_ok=True)
        return path

    def get(self, key: str):
        value = self.redis.get(self.prefix + key)
        return json.loads(value.decode()) if value else None

    def mature_markers(self, minimum_age_seconds: int = 600):
        for path in self.marker_dir.iterdir():
            parts = path.name.split("_")
            if (
                len(parts) != 3
                or not parts[0].isdigit()
                or len(parts[1]) != 32
                or len(parts[2]) != 40
            ):
                continue
            if int(self.clock()) - int(parts[0]) >= minimum_age_seconds:
                yield path, parts[0], "%s_%s" % (parts[1], parts[2])

    @staticmethod
    def acknowledge(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
