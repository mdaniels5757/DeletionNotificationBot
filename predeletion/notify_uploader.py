import pprint
import re
import hashlib
import time
import pywikibot
import datetime
from cryptography.fernet import Fernet
import os
import sys
from tqdm import tqdm


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import PUBFILEDIR
import pubsub
from utils import deletion_categories, commit
from config import KEY

yesterday = datetime.date.today() - datetime.timedelta(days=1)

yesterday_hash_list = [
    "Deletion requests %s" % yesterday.strftime("%B %Y"),
    "Media without a license as of %s" % yesterday.strftime("%-d %B %Y"),
    "Media missing permission as of %s" % yesterday.strftime("%-d %B %Y"),
    "Media without a source as of %s" % yesterday.strftime("%-d %B %Y"),
]

deletion_categories = deletion_categories + yesterday_hash_list

md5_deletion_categories = [
    hashlib.md5(cat.encode("utf-8")).hexdigest() for cat in deletion_categories
]


def delete_file(file):
    try:
        os.remove(file)
    except OSError:
        pass


def handle_if_uploader_knows(redis_file_name):
    print("NOT NOTIFYING : Uploader knows about the deletion")
    delete_file(redis_file_name)


def handle_if_a_moved_file_redirect(redis_file_name):
    print("NOT NOTIFYING : is_a_moved_file_redirect")
    delete_file(redis_file_name)


def handle_if_uploader_is_nominator(uploader, redis_file_name):
    print(
        "NOT NOTIFYING : Uploader (User:%s) themselve nominated their own upload for deletion, nothing to do here!"
        % uploader
    )
    delete_file(redis_file_name)


def does_the_uploader_know(uploader, file_name, subpage=None):
    uploader_talk_page_name = "User_talk:%s" % uploader

    uploader_talk_page = pywikibot.Page(SITE, uploader_talk_page_name)

    if uploader_talk_page.isRedirectPage():
        redirect_target = uploader_talk_page.getRedirectTarget()
        redirect_target_title = redirect_target.title()
        if not redirect_target.isTalkPage():

            if "user:" in redirect_target_title.lower():
                redirect_target = redirect_target.getUserTalkPage()
                redirect_target_title = redirect_target.title()
                uploader_talk_page = redirect_target
                print(
                    "Talk page redirected from '%s' to '%s'"
                    % (uploader_talk_page_name, redirect_target_title)
                )
        else:
            print(
                "Talk page redirected from '%s' to '%s'"
                % (uploader_talk_page_name, redirect_target_title)
            )
            uploader_talk_page = redirect_target

    uploader_talk_page_text = uploader_talk_page.get()

    if (
        file_name.replace(" ", "_").lower()
        in uploader_talk_page_text.replace(" ", "_").lower()
    ):
        print("file_name in uploader_talk_page_text")
        return True

    if subpage:
        # subpage_name = "Commons:Deletion requests/" + subpage
        # see issue at https://commons.wikimedia.org/w/index.php?diff=602311329&oldid=602310441
        # The namespace is usually not used in the templates but the subapge.
        subpage_name = subpage.strip()
        print(subpage_name)
        if (
            subpage_name.replace(" ", "_").lower()
            in uploader_talk_page_text.replace(" ", "_").lower()
        ):
            print("subpage_name in uploader_talk_page_text")
            return True

        subpage_name = "Commons:Deletion requests/" + subpage.strip()    
        page = pywikibot.Page(SITE, subpage_name)
        if not page.exists():
            return False
        else:
            subpage_text = page.get()
            if (
                file_name.replace(" ", "_").lower()
                in subpage_text.replace(" ", "_").lower()
            ):
                all_editors = list(page.contributors(total=100).keys())
                if uploader in all_editors:
                    print("uploader edited the subpage and filename in subpage_text")
                    return True
    return False


def data_printer(
    file_name,
    nominator,
    uploader,
    uploader_is_nominator,
    deletion_category,
    is_a_moved_file_redirect,
    nomination_time,
    latest_revision_time,
    latest_revision_sha1,
    nomination_reason,
):
    text = (
        "\n--------------------------"
        + "\nfile_name : %s" % file_name
        + "\nnominator : %s" % nominator
        + "\nuploader : %s" % uploader
        + "\nuploader_is_nominator : %s" % uploader_is_nominator
        + "\ndeletion_category : %s" % deletion_category
        + "\nis_a_moved_file_redirect : %s" % is_a_moved_file_redirect
        + "\nnomination_time : %s" % nomination_time
        + "\nlatest_revision_time : %s" % latest_revision_time
        + "\nlatest_revision_sha1 : %s" % latest_revision_sha1
        + "\nnomination_reason : %s" % nomination_reason
    )

    print(text)


def submit(notice, uploader, deletion_category, file_count, first_file_name):
    notice = (
        notice
        + "\nI'm a computer program; please don't ask me questions but ask the user who nominated your file(s) for deletion or at our [[Commons:Help_desk|Help Desk]]. //~~~~"
    )
    if file_count > 1:
        more_than_one_files = "and %d other file(s)" % (file_count - 1)
    else:
        more_than_one_files = " "

    summary = "Impending deletion notification - [[Category:%s|%s]] - [[:%s]] %s" % (
        deletion_category,
        deletion_category,
        first_file_name,
        more_than_one_files,
    )

    uploader_talk_page_name = "User_talk:%s" % uploader

    uploader_talk_page = pywikibot.Page(SITE, uploader_talk_page_name)

    old_text = uploader_talk_page.get()
    new_text = old_text + notice
    # pywikibot.showDiff(old_text, new_text)
    print("SUMMARY: %s" % summary)

    commit(old_text, new_text, uploader_talk_page, summary)


def decrypt_data(data):
    cipher_suite = Fernet(KEY.encode())
    return cipher_suite.decrypt(data.encode()).decode()


def notifiable(
    is_a_moved_file_redirect,
    redis_file_name,
    nominator,
    uploader,
    file_name,
    subpage=None,
):
    if is_a_moved_file_redirect == "True":
        handle_if_a_moved_file_redirect(redis_file_name)
        return False

    if nominator == uploader:
        handle_if_uploader_is_nominator(uploader, redis_file_name)
        return False

    if nominator == "AntiCompositeBot":
        print("AntiCompositeBot's piece of the cake.")
        return False

    if does_the_uploader_know(uploader, file_name, subpage=subpage):
        handle_if_uploader_knows(redis_file_name)
        return False

    return True


def data_parser(data):
    file_name = decrypt_data(data["file_name"])
    nominator = decrypt_data(data["nominator"])
    uploader = decrypt_data(data["uploader"])
    uploader_is_nominator = decrypt_data(data["uploader_is_nominator"])
    deletion_category = decrypt_data(data["deletion_category"])
    is_a_moved_file_redirect = decrypt_data(data["is_a_moved_file_redirect"])
    nomination_time = decrypt_data(data["nomination_time"])
    latest_revision_time = decrypt_data(data["latest_revision_time"])
    latest_revision_sha1 = decrypt_data(data["latest_revision_sha1"])
    nomination_reason = decrypt_data(data["nomination_reason"])
    redis_file_name = PUBFILEDIR + data["redis_file_name"]
    return (
        file_name,
        nominator,
        uploader,
        uploader_is_nominator,
        deletion_category,
        is_a_moved_file_redirect,
        nomination_time,
        latest_revision_time,
        latest_revision_sha1,
        nomination_reason,
        redis_file_name,
    )


def handle_advertisements_speedy_deletion(uploader_and_uploads):
    print("\n\n\nHANDLING 'advertisements_speedy_deletion'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = (
                    notice
                    + "\n\n== [[:%s]] ==\n{{User:Deletion Notification Bot/NOADS/headingless|1=%s}}"
                    % (file_name, file_name)
                )
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_copyright_violation(uploader_and_uploads):
    print("\n\n\nHANDLING 'copyright_violation'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = notice + "\n\n{{subst:Copyvionote|1=%s|2=%s|3=}} " % (
                    file_name,
                    nomination_reason,
                )
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_other_speedy_deletion(uploader_and_uploads):
    print("\n\n\nHANDLING 'other_speedy_deletion'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = (
                    notice
                    + "\n\n== [[:%s]] ==\n{{User:Deletion Notification Bot/SDEL/headingless|1=%s|2=%s}}"
                    % (file_name, file_name, nomination_reason)
                )
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_personal_files_for_speedy_deletion(uploader_and_uploads):
    print("\n\n\nHANDLING 'personal_files_for_speedy_deletion'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = (
                    notice
                    + "\n\n== [[:%s]] ==\n{{User:Deletion Notification Bot/personalNO/headingless|1=%s}}"
                    % (file_name, file_name)
                )
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_deletion_requests(uploader_and_uploads):
    print("\n\n\nHANDLING 'deletion_requests'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            match = re.search(
                r"^REASON:\|###(.*?)###-SUBPAGE:###(.*?)###$", nomination_reason
            )

            nomination_reason = match.group(1)
            subpage = match.group(2)

            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
                subpage=subpage,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = notice + "\n{{subst:idw|1=%s|2=%s}}" % (file_name, subpage)
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = (
                    "Entry page : [[Commons:Deletion requests/%s]]" % subpage
                )
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_media_without_license(uploader_and_uploads):
    print("\n\n\nHANDLING 'media_without_license'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = notice + "\n{{subst:image license|1=%s}}" % file_name
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_media_missing_permission(uploader_and_uploads):
    print("\n\n\nHANDLING 'media_missing_permission'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = notice + "\n{{subst:image permission|1=%s}}" % file_name
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def handle_media_without_source(uploader_and_uploads):
    print("\n\n\nHANDLING 'media_without_source'")
    _i = 0
    for uploader, data_list in uploader_and_uploads.items():
        _i += 1
        print("\nFiles uploaded by %s" % uploader)
        notice = ""
        i = 0
        file_count = 0
        for data in data_list:
            (
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
                redis_file_name,
            ) = data_parser(data)
            data_printer(
                file_name,
                nominator,
                uploader,
                uploader_is_nominator,
                deletion_category,
                is_a_moved_file_redirect,
                nomination_time,
                latest_revision_time,
                latest_revision_sha1,
                nomination_reason,
            )

            if not notifiable(
                is_a_moved_file_redirect,
                redis_file_name,
                nominator,
                uploader,
                file_name,
            ):
                continue

            i += 1
            if i == 1:
                first_file_name = file_name
                notice = notice + "\n{{subst:Image source |1=%s}}" % file_name
                notice = notice + (
                    """\n<p style="font-size:0.8em;font-family:'Stencil Std'">\nUser who nominated the file for deletion (Nominator) : {{Noping|%s}}.</p>"""
                    % nominator
                )
            else:
                nominator_details = "Nominator : {{Noping|%s}}" % nominator
                nomination_details = "Reason : %s" % nomination_reason
                if i == 2:
                    notice = notice + "\nAnd also:"
                notice = notice + (
                    """\n* [[:%s]] <span style="font-size:0.8em;font-family:'Stencil Std'">( %s  &#124;  %s )</span>"""
                    % (file_name, nominator_details, nomination_details)
                )
            file_count = i
            delete_file(redis_file_name)
        if file_count > 0:
            submit(notice, uploader, deletion_category, file_count, first_file_name)

    if _i == 0:
        print("No files found")


def main(*args):
    args = pywikibot.handle_args(*args)
    global SITE
    SITE = pywikibot.Site()
    print(SITE)
    if not SITE.logged_in():
        SITE.login()

    list1 = []
    list2 = []
    list3 = []
    list4 = []
    list5 = []
    list6 = []
    list7 = []
    list8 = []

    # we are repeating the 5,6,7,8 as the MD5 hash of the cats varies for atleast once
    # a day in a month. And as much as every day.
    lists = [
        list1,
        list2,
        list3,
        list4,
        list5,
        list6,
        list7,
        list8,
        list5,
        list6,
        list7,
        list8,
    ]

    for filename in os.listdir(PUBFILEDIR):
        match = re.search(r"([0-9]{10})_([a-fA-F\d]{32})_([a-fA-F\d]{40})", filename)
        if not match:
            continue
        unix_timestamp = match.group(1)
        category_md5_hash = match.group(2)
        latest_revision_sha1 = match.group(3)
        index_in_list = md5_deletion_categories.index(category_md5_hash)
        category = deletion_categories[index_in_list]
        file_cat_list = lists[index_in_list]
        data = (category, latest_revision_sha1, unix_timestamp, category_md5_hash)
        file_cat_list.append(data)

    i = 0
    for _list in lists[0:8:1]:
        i += 1
        uploader_and_uploads = {}
        for data in _list:
            category = data[0]
            latest_revision_sha1 = data[1]
            unix_timestamp = data[2]
            category_md5_hash = data[3]

            minutes = (int(time.time()) - int(unix_timestamp)) // 60
            if minutes >= 10:
                key = category_md5_hash + "_" + latest_revision_sha1
                value = pubsub.get(key)

                if not value:
                    continue

                value["redis_file_name"] = (
                    unix_timestamp
                    + "_"
                    + category_md5_hash
                    + "_"
                    + latest_revision_sha1
                )

                uploader = decrypt_data(value.get("uploader"))
                if uploader_and_uploads.get(uploader):
                    value_list = uploader_and_uploads.get(uploader)
                    value_list.append(value)
                else:
                    uploader_and_uploads[uploader] = [value]

        if i == 1:
            handle_advertisements_speedy_deletion(uploader_and_uploads)
        elif i == 2:
            handle_copyright_violation(uploader_and_uploads)
        elif i == 3:
            handle_other_speedy_deletion(uploader_and_uploads)
        elif i == 4:
            handle_personal_files_for_speedy_deletion(uploader_and_uploads)
        elif i == 5:
            handle_deletion_requests(uploader_and_uploads)
        elif i == 6:
            handle_media_without_license(uploader_and_uploads)
        elif i == 7:
            handle_media_missing_permission(uploader_and_uploads)
        elif i == 8:
            handle_media_without_source(uploader_and_uploads)
        else:
            pass


if __name__ == "__main__":
    while True:
        try:
            main()
            min = 10
            print("\n\nSLEEP FOR '%d minutes'" % min)
            for i in tqdm(range(min)):
                time.sleep(60)  # 60 = 1 min
        except Exception as err:
            print(err)
