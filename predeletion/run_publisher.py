import os
import sys
from datetime import UTC, datetime

import pywikibot

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import eventstreams
import publisher
import utils
from policies import HOTWORDS

hot_words = [hotword for category in HOTWORDS.values() for hotword in category]
SITE: pywikibot.site.BaseSite


def nominated_for_deletion_in_this_change(file_name: str, user: str, timestamp: str):
    page = pywikibot.Page(SITE, file_name)
    found_cats = []
    deletion_cat = None

    for cat in page.categories():
        cat_title = cat.title(with_ns=False)
        found_cats.append(cat_title)

    for cat in utils.deletion_categories:
        if cat in found_cats:
            deletion_cat = cat
            break

    if not deletion_cat:
        return False

    revision = utils.revision_that_added_the_text_first(SITE, file_name, hot_words)

    if revision and revision.user and revision.timestamp:
        str_timestamp = datetime.fromtimestamp(
            int(timestamp), tz=UTC
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        result = revision.user == user and revision.timestamp == str_timestamp
        print(
            "nominated_for_deletion_in_this_change: "
            f"user: {user}, revision.user: {revision.user}, "
            f"timestamp: {str_timestamp}, revision.timestamp: {revision.timestamp}. "
            f"result: {result}"
        )
        return result

    return False


def main():
    global SITE
    SITE = pywikibot.Site()

    if not SITE.logged_in():
        SITE.login()

    for change in eventstreams.recentchanges():
        if nominated_for_deletion_in_this_change(
            change.title, change.user, change.timestamp
        ):
            file_nominated_for_deletion = publisher.FileNominatedForDeletion(
                change.title
            )
            print(repr(file_nominated_for_deletion))
            file_nominated_for_deletion.publish()
        if (
            datetime.now(tz=UTC).time().minute == 24
            and datetime.now(tz=UTC).time().second >= 30
            and datetime.now(tz=UTC).time().hour % 4 == 0
        ):
            print("Stopping for a restart")
            exit()


if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as err:
            print(err)
