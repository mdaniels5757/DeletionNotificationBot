"""Recipient preferences stored on Commons."""

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationPreferences:
    notifications: bool = True
    notify_redirects: bool = True

    @classmethod
    def from_json(cls, text: str) -> "NotificationPreferences":
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("configuration must be a JSON object")
        unknown = data.keys() - {"notifications", "notify_redirects"}
        if unknown:
            raise ValueError("configuration contains unknown settings")
        values = {}
        for key in ("notifications", "notify_redirects"):
            if key in data:
                if not isinstance(data[key], bool):
                    raise ValueError(f"{key} must be a boolean")
                values[key] = data[key]
        return cls(**values)
