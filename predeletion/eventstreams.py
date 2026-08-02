from typing import Generator
from dataclasses import dataclass
from sseclient import SSEClient as EventSource
import json


def stream():
    recentchange_stream_url = "https://stream.wikimedia.org/v2/stream/recentchange"
    for event in EventSource(recentchange_stream_url):
        if event.event == "message" and event.data:
            try:
                data = json.loads(event.data)
            except json.decoder.JSONDecodeError as e:
                print("eventstreams JSONDecodeError %s\n%s " % (e, event.data))
                continue
            if (
                (data["type"] == "edit")
                and (not data["bot"])
                and (data["meta"]["domain"] == "commons.wikimedia.org")
                and (data["namespace"] == 6)
            ):
                yield data

        if event.event == "error":
            print("###ERROR : Event stream error ", event.data)


@dataclass(frozen=True, kw_only=True)
class Change:
    title: str
    comment: str
    revisionid: int
    parsedcomment: str
    user: str
    timestamp: str


def recentchanges() -> Generator[Change, None, None]:
    for data in stream():
        print(data)
        change = Change(
            title=data["title"],
            comment=data["comment"],
            revisionid=data["revision"]["new"],
            parsedcomment=data["parsedcomment"],
            user=data["user"],
            timestamp=data["timestamp"],
        )
        print(change.title, change.comment, change.revisionid, change.parsedcomment)
        yield change


if __name__ == "__main__":
    for change in recentchanges():
        print(change)
