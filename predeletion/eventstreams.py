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


def recentchanges():
    for data in stream():
        # print(data)
        title = data["title"]
        comment = data["comment"]
        revisionid = data["revision"]["new"]
        parsedcomment = data["parsedcomment"]
        user = data["user"]
        timestamp = data["timestamp"]
        # print(title, comment, revisionid, parsedcomment)
        yield (title, comment, revisionid, parsedcomment, user, timestamp)


if __name__ == "__main__":
    for change in recentchanges():
        print(change)
