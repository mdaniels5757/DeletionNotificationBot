import datetime
import pywikibot
from urllib3.exceptions import HTTPError

today = datetime.datetime.utcnow()

deletion_categories = [
    "Advertisements for speedy deletion",  # 0
    "Copyright violations",  # 1
    "Other speedy deletions",  # 2
    "Personal files for speedy deletion",  # 3
    "Deletion requests %s" % today.strftime("%B %Y"),  # 4
    "Media without a license as of %s" % today.strftime("%-d %B %Y"),  # 5
    "Media missing permission as of %s" % today.strftime("%-d %B %Y"),  # 6
    "Media without a source as of %s" % today.strftime("%-d %B %Y"),  # 7
]


def revision_that_added_the_text_first(SITE, pagename, texts_to_search, **kwargs):
    """
    Find the revision of the page if which any of the text in texts_to_search
    was first added.

    :param SITE: pywikibot.Site() object. Used to identify the site.
    :param pagename: name of the page on which we are going to search for the
                     the text in texts_to_search.
    :param texts_to_search: List of string that we we want to search for
                            in the page.
    :param search_the_edit_summary: For a revision along the revision page text
                                    also search the revision edit summary.
                                    Default is True, set to False if not to
                                    search the edit summary. Use boolean only.
    :param number_of_revisions_to_check: How many revisions to iterate before
                                         giving up. We can't ever be sure that
                                         we will match anything and for pages
                                         with huge revision tables we need to
                                         set a max number of revisions.
                                         Default is '500' revisions. Use integer
                                         only.
    """

    if kwargs.get("search_the_edit_summary"):
        search_the_edit_summary = kwargs.get("search_the_edit_summary")

    else:
        search_the_edit_summary = True

    if kwargs.get("number_of_revisions_to_check"):
        number_of_revisions_to_check = kwargs.get("number_of_revisions_to_check")

    else:
        number_of_revisions_to_check = 500

    page = pywikibot.Page(SITE, pagename)
    history = (page).revisions(
        content=True, reverse=False, total=number_of_revisions_to_check
    )
    found_nom = False
    timestamp = False
    data = ()

    for revdata in history:

        content = revdata["slots"]["main"]["*"].lower()
        edit_summary = revdata.comment.lower()
        user = revdata.user
        text_to_be_searched = content

        if search_the_edit_summary:
            text_to_be_searched = text_to_be_searched + "\n" + edit_summary

        if found_nom:

            if data[3].lower() not in text_to_be_searched:
                return data

            else:

                found_nom = False
                timestamp = None
                data = ()

        for text in texts_to_search:

            if text.lower() in text_to_be_searched:

                found_nom = True
                timestamp = revdata.timestamp
                data = (user, content, edit_summary, text, timestamp)
                break

    # For cases when the oldest revision has the text we are looking for but
    # we exhaust the history and break out of the look.
    if found_nom:

        return data

    else:

        return None


def out(text, newline=True, date=False, color=None):
    """
    output text to the terminal / log.

    :param text: The text we want to output.
    :param newline: If True, a line feed will be added after the text.
    :param date: Output the date and time.
    :param color: Color of the output text.
    """

    if color:

        text = "\03{%s}%s\03{default}" % (color, text)

    date_string = "%s: " % today.strftime("%Y-%m-%d %H:%M:%S") if date else ""

    pywikibot.stdout("%s%s" % (date_string, text), newline=newline)


def commit(old_text, new_text, page, summary):
    """
    Show diff between old and new text and save the page with the new text.

    :param old_text: Old text of the page. Used for showing the diff.
    :param new_text: The complete text of the revised page.
    :param page: pywikibot.Page(SITE, "page_name") object.
    :param summary: The edit summary for the modification.
    """

    out("\nAbout to edit the page : '%s'" % page.title())

    pywikibot.showDiff(old_text, new_text)

    page.put(new_text, summary=summary, watch="nochange", minor=False)


def page_creator(page, link=False, obj=False):
    """
    User of created the page, they made the first revision on the page.

    :param page: pywikibot.Page(SITE, "name_of_page") object.
    :param link: If True then return a wikilink, e.g. [[User:Ken|Ken]]
                 for user Ken.
    :param obj: If True then return a pywikibot.User(SITE, "user_name") object.
    """

    # reverse=True is to get the revisions in FIFO
    # and total=1 as we want only the first revision.
    revisions = page.revisions(reverse=True, total=1)

    # As total=1, we should loop only once.
    for revision in revisions:
        username = revision.user

    if not revisions:
        # history
        return "Unknown"

    if link:
        # wikilink, e.g. [[User:UserName|UserName]]
        return "[[User:%s|%s]]" % (username, username)

    if obj:
        # pywikibot user object
        return pywikibot.User(SITE, username)

    # return just the username without namespace "User:", e.g. will
    # return 'ExampleEditor' for 'User:ExampleEditor'
    return username


def is_locked(user):
    """
    Check if an user is globally locked user. They are banned from
    all the wikis. And we should not be notifying them about deletions.

    Every user on wikimedia wikis has an account on login.wikimedia.org and
    we leverage this info to check the 'globaluserinfo' and verify whether
    the passed user is globally locked or not.

    :param user: User to check for globally blocked account status.
    """
    headers = {"user-agent": "User:Deletion Notification Bot @ wikimedia Commons"}

    try:

        response = requests.get(
            "https://login.wikimedia.org/w/api.php?action=query&meta=globaluserinfo&format=json&guiuser=%s"
            % user,
            headers=headers,
        )

    except HTTPError as http_err:

        print("HTTP error occurred: %s" % http_err)

    except Exception as err:

        print("Other error occurred: %s" % err)

    if response.ok:
        data = response.json()

        if (data.get("query").get("globaluserinfo").get("locked", False)) is False:
            return False

        else:
            return True

    else:
        return True
