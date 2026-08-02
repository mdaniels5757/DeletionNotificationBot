import pywikibot
from datetime import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import eventstreams
import hotwords
import publisher
import utils


hot_words = (
    hotwords.advertisements_speedy_deletion_hot_words
    + hotwords.copyright_violations_hot_words
    + hotwords.other_speedy_deletions_hot_words
    + hotwords.personal_files_for_speedy_deletion_hot_words
    + hotwords.deletion_requests_hot_words
    + hotwords.media_without_a_license_hot_words
    + hotwords.media_missing_permission_hot_words
    + hotwords.media_without_a_source_hot_words
)


def nominated_for_deletion_in_this_change(file_name, user, timestamp):
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

    if not revision:
        return False

    (
        nominator,
        content,
        comment,
        matched_hotword,
        nomination_time,
    ) = revision

    if nominator and nomination_time:
        str_timestamp = datetime.utcfromtimestamp(timestamp).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        if (str(nominator) == str(user)) and (
            str(nomination_time) == str(str_timestamp)
        ):
            return True

    return False


def main(*args):
    args = pywikibot.handle_args(*args)

    global SITE
    SITE = pywikibot.Site()

    if not SITE.logged_in():
        SITE.login()

    for change in eventstreams.recentchanges():
        title = change[0]
        user = change[4]
        timestamp = change[5]

        if nominated_for_deletion_in_this_change(title, user, timestamp):

            file_nominated_for_deletion = publisher.FileNominatedForDeletion(title)
            print(repr(file_nominated_for_deletion))
            file_nominated_for_deletion.publish()
        if datetime.now().time().minute == 24 and datetime.now().time().second >= 30 and datetime.now.time().hour % 4 == 0:
            print('Stopping for a restart')
            exit()

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as err:
            print(err)
