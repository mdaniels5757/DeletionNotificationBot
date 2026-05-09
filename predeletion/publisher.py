import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import re
import config
import pubsub
import hashlib
import hotwords
import datetime
import pywikibot
from pywikibot.exceptions import NoPageError
from cryptography.fernet import Fernet
from utils import (
    is_locked,
    deletion_categories,
    out,
    commit,
    revision_that_added_the_text_first,
    page_creator,
    today,
)


SITE = pywikibot.Site()


class NominatorAndNomination:
    """
    A NominatorAndNomination instance represents a file's nominator and the
    nomination itself.

    NominatorAndNomination instances are created every time the nomination
    information including but not limited to the nominator are wanted. they
    contain all the information pertinent to the nomination of the passed file.
    The only information passed is the file name. The instance also includes
    information such as time of nomination and the reason for nominating the
    file.
    """

    def __init__(self, file_name, deletion_category):
        """
        Initialize a NominatorAndNomination instance with the passed file name
        and also initializing some other variables.
        """
        self.file_name = file_name
        self.deletion_category = deletion_category
        self.nomination_reason = None
        self.nominator = None
        self.nomination_time = None
        self.invoke_category_nominator_method()

    def invoke_category_nominator_method(self):
        if "Advertisements for speedy deletion" in self.deletion_category:
            self.advertisements_speedy_deletion_nominator_finder()

        elif "Copyright violations" in self.deletion_category:
            self.copyright_violations_nominator_finder()

        elif "Other speedy deletions" in self.deletion_category:
            self.other_speedy_deletions_nominator_finder()

        elif "Personal files for speedy deletion" in self.deletion_category:
            self.personal_files_for_speedy_deletion_nominator_finder()

        elif "Deletion requests" in self.deletion_category:
            self.deletion_requests_nominator_finder()

        elif "Media without a license as of" in self.deletion_category:
            self.media_without_a_license_nominator_finder()

        elif "Media missing permission as of" in self.deletion_category:
            self.media_missing_permission_nominator_finder()

        elif "Media without a source as of" in self.deletion_category:
            self.media_without_a_source_nominator_finder()

    def set_nominator_and_nomination_time(self, hotwords):
        """
        Set the nominator and nomination time of the file.

        The 'revision_that_added_the_text_first' method iterates through
        the revisions while search for the hotwords in the edit summaries
        or the page text of the revision. Once the revision is identified
        it returns revision attributes such as editor(nominator), content,
        comment(edit summary), edit time (nomination time) and the hotword
        which was found in the revision.

        :param hotwords: List of words used to commonly nominate the
                       file for deletion. e.g. part of templates like
                       '{{copyvio' or commnets made by semi-automated scripts
                       like 'Marking as possible copyvio'. The hotwords, the
                       page text and comments are lowercased before searching.
        """
        nomination_revsion_data = revision_that_added_the_text_first(
            SITE, self.file_name, hotwords
        )

        if nomination_revsion_data:
            (
                nominator,
                content,
                comment,
                matched_hotword,
                nomination_time,
            ) = nomination_revsion_data
            self.nominator = nominator
            self.nomination_time = nomination_time

    def advertisements_speedy_deletion_nominator_finder(self):
        """
        Find the user who nominated the file for deletion under the
        criteria for speedy deletion.

        We have certain 'hotwords' that are used to identify the
        nominator, we iterate through the revisions of the page and
        try to find the revision that added any of the hotwords.

        Usually hotwords are the templates and edit summaries commonly
        used while nominating the file for deletion. Some scripts will
        always generate the same edit summaries and there are selected
        number of templates that can be used, we leverage this information
        to accuratly identify the nominator.
        """
        self.set_nominator_and_nomination_time(
            hotwords.advertisements_speedy_deletion_hot_words
        )
        self.set_advertisements_speedy_deletion_nomination_reason()

    def set_advertisements_speedy_deletion_nomination_reason(self):
        """Set nomination reason for advertisement speedy deletion"""
        self.nomination_reason = (
            "[[Special:MyLanguage/COM:CSD#G10|CSD G10]] "
            + "(files and pages created as advertisements)"
        )

    def copyright_violations_nominator_finder(self):
        self.set_nominator_and_nomination_time(hotwords.copyright_violations_hot_words)
        self.set_copyright_violations_nomination_reason()

    def set_copyright_violations_nomination_reason(self):
        # print(f"Getting text, line 142")
        text = pywikibot.Page(SITE, self.file_name).get()
        text = re.sub(
            r"\(\[\[User talk:(?:.*?)\|<span class=\"signature(?:.*)\(UTC\)", " ", text
        )
        l_text = text.lower()
        match = re.search(r"{{(?:\s*?|)(?:db\-|)[Cc]opyvio(?:\s*?|)\|(.*?)}}", text)
        if match:
            reason = match.group(1)
            reason = reason.replace("1=", " ").replace("source=", " ").replace("|", " ")
            # Not sure why I commented out '.replace("|", " ")' on 20250421, because it's needed:
            # see https://commons.wikimedia.org/wiki/Special:Permalink/1071557850 -- Mdaniels 20250814
        else:
            if re.search(r"{{(?:\s*?|)logo(.*?)}}", text):
                reason = "File is not a freely licensed logo"

            elif "{{sd|f1" in l_text:
                reason = "[[Commons:Criteria_for_speedy_deletion#F1|Apparent copyright violation]]"

            elif "{{sd|f2" in l_text:
                reason = "[[Commons:Criteria_for_speedy_deletion#F2|Fair use content]]"

            elif "{{sd|f3" in l_text:
                reason = "[[Commons:Criteria_for_speedy_deletion#F3|Derivative work of non-free content]]"

            elif "{{sd|f4" in l_text:
                reason = (
                    "[[Commons:Criteria_for_speedy_deletion#F4|Failed license review]]"
                )

            elif "{{sd|f5" in l_text:
                reason = "[[Commons:Criteria_for_speedy_deletion#F5|Missing essential information]]"

            elif "{{sd|f6" in l_text:
                reason = (
                    "[[Commons:Criteria_for_speedy_deletion#F6|License laundering]]"
                )

            elif "{{sd|f7" in l_text:
                reason = (
                    "[[Commons:Criteria_for_speedy_deletion#F7|File is "
                    + "empty, corrupt, or in a disallowed format]]"
                )

            elif "{{sd|f8" in l_text:
                reason = "[[Commons:Criteria_for_speedy_deletion#F8|Exact or scaled-down duplicate]]"

            elif "{{sd|f9" in l_text:
                reason = (
                    "[[Commons:Criteria_for_speedy_deletion#F9|The file"
                    + " contains additional embedded data in the form of a password protected archive.]]"
                )

            elif "{{sd|f10" in l_text:
                reason = (
                    "[[Commons:Criteria_for_speedy_deletion#F10|Personal"
                    + " photos by non-contributors]]"
                )

            elif "{{copyvio}}" in l_text:
                reason = "Copyright infringement / piracy"

            else:
                reason = ""

        self.nomination_reason = re.sub(r"[Cc]ategory:", ":Category:", reason)

    def other_speedy_deletions_nominator_finder(self):
        self.set_nominator_and_nomination_time(
            hotwords.other_speedy_deletions_hot_words
        )
        self.other_speedy_deletions_nomination_reason()

    def other_speedy_deletions_nomination_reason(self):
        # print(f"Getting text, line 214")
        text = pywikibot.Page(SITE, self.file_name).get()

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)1(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G1|CSD G1]] "
                + "(Test page, accidental creation, or page containing nonsense or no valid content)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)2(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G2|CSD "
                + "G2]] (Unused and implausible, or broken redirect)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)3(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G3|CSD"
                + " G3]] (Content intended as vandalism, threat, or attack)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)4(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G4|CSD G4]]"
                + " (Recreation of content previously deleted per community consensus)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)5(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G5|CSD "
                + "G5]] (Temporary deletion for history cleaning or revision suppression)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)6(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G6|CSD G6]] (Uncontroversial maintenance)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)7(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = "[[Special:MyLanguage/COM:CSD#G7|CSD G7]] (Author or uploader request deletion)"

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)8(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G8|CSD"
                + " G8]] (Page dependent on deleted or non-existent content)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)9(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G9|CSD"
                + " G9]] (Wikimedia Foundation office action)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)10(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G10|CSD"
                + " G10]] (Files and pages created as advertisements)"
            )

        if re.search(
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)11(?:\s*?|)}}",
            text,
        ):
            self.nomination_reason = (
                "[[Special:MyLanguage/COM:CSD#G11|CSD"
                + " G11]] (Blatant text copyright violation)"
            )

        regexp = r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|1=[Gg])[0-9]{1,2}(?:\s*?|)(?:\|2=|)(.*?)}}"
        match = re.search(
            regexp,
            text,
        )
        if match and not self.nomination_reason:
            reason = (
                match.group(1).replace("1=", " ").replace("2=", " ").replace("|", " ") # Commented out this replacement -- MDaniels 20250421
                # Uncommented .replace("|", " ") per [[Special:Permalink/1124217287]]
            )
            self.nomination_reason = re.sub(r"[Cc]ategory:", ":Category:", reason)
        regexp = r"{{(?:\s*?|)(?:[Ss]peedy|[Cc]sd|SD\|1=G7|2=|[Dd]b\-g7|[Ss]peedy\s*?[Dd]elet(?:e|ion))(?:\s*?|)\|(.*?)}}"
        match = re.search(
            regexp,
            text,
        )
        if match and not self.nomination_reason:
            reason = match.group(1).replace("1=", " ").replace("|", " ") #Commented out this replacement -- MDaniels 20250421
            # Uncommented per [[Special:Permalink/1028879132#Duplicated_argument_on_deletion_notification]] -- MD 20250507
            self.nomination_reason = re.sub(r"[Cc]ategory:", ":Category:", reason)

    # personal_files_for_speedy_deletion
    def personal_files_for_speedy_deletion_nominator_finder(self):
        self.set_nominator_and_nomination_time(
            hotwords.personal_files_for_speedy_deletion_hot_words
        )
        self.personal_files_for_speedy_deletion_nomination_reason()

    def personal_files_for_speedy_deletion_nomination_reason(self):
        self.nomination_reason = (
            "[[Special:MyLanguage/COM:CSD#F10|CSD F10]]"
            + " (personal photos by non-contributors)"
        )

    def deletion_requests_nominator_finder(self):
        self.set_nominator_and_nomination_time(hotwords.deletion_requests_hot_words)
        self.deletion_requests_nomination_reason()

    def deletion_requests_nomination_reason(self):
        # print(f"Getting page, line 349")
        page = pywikibot.Page(SITE, self.file_name)
        # print(f"Getting text, line 351")
        text = page.get()

        subpage = None
        reason = None

        # find_subpage
        match = re.search(
            r"{{(?:\s*?|)[Dd]elete(?:\s*?|)(?:.*?)\|subpage=(.*?)\|(?:.*?)}}", text
        )
        if match:
            subpage = match.group(1).strip()
            pass

        # try to find reason in file page.
        match = re.search(
            r"{{(?:\s*?|)[Dd]elete(?:\s*?|)(?:.*?)\|reason=(.*?)\|(?:.*?)}}", text
        )
        if match:
            reason = match.group(1).strip()

        # No need to worry about the reason as the template don't support reason param.
        if not reason:
            reason = "REASONNOTFOUND"

        # Must find the subpage, it's the must pass param of idw template.
        # We will now look in all the pages that links to the file and have the DR prefix
        # and we may hit the jackpot and find the subpage.
        if not subpage:
            # print(f"Getting backlinks, line 380")
            backlinks = page.backlinks(follow_redirects=True, namespaces=4)

            for page in backlinks:
                title = page.title()
                if not "Commons:Deletion requests/" in title:
                    continue
                if "Commons:Deletion requests/%s" % today.strftime("%Y") in title:
                    continue
                _subpage = pywikibot.Page(SITE, title)
                _subpage_text = _subpage.get()
                file_name_with_underscore = self.file_name.replace(" ", "_")
                underscore_instead_of_spaces_subpage_text = _subpage_text.replace(
                    " ", "_"
                )
                if (
                    file_name_with_underscore
                    in underscore_instead_of_spaces_subpage_text
                ):
                    subpage = title.replace("Commons:Deletion requests/", "")

        if not subpage:
            subpage = "CANNOTFINDTHESUBPAGE"
        self.nomination_reason = "REASON:|###%s###-SUBPAGE:###%s###" % (reason, subpage)

    def media_without_a_license_nominator_finder(self):
        self.set_nominator_and_nomination_time(
            hotwords.media_without_a_license_hot_words
        )
        self.media_without_a_license_nomination_reason()

    def media_without_a_license_nomination_reason(self):
        self.nomination_reason = (
            "This media file does not have sufficient information on its "
            + "copyright status. If you have created this file yourself, "
            + "or the file is in the public domain, you can edit the file "
            + "description page to license it under one of the allowed licenses."
        )

    def media_missing_permission_nominator_finder(self):
        self.set_nominator_and_nomination_time(
            hotwords.media_missing_permission_hot_words
        )
        self.media_missing_permission_nomination_reason()

    def media_missing_permission_nomination_reason(self):
        self.nomination_reason = "This media file is missing evidence of permission."

    def media_without_a_source_nominator_finder(self):
        self.set_nominator_and_nomination_time(
            hotwords.media_without_a_source_hot_words
        )
        self.media_without_a_source_nomination_reason()

    def media_without_a_source_nomination_reason(self):
        self.nomination_reason = (
            "This media file is a derivative work incorporating another work or works. "
            + "While the source of this file has been identified, essential source "
            + "information for all work incorporated in this file is missing."
        )


class FileNominatedForDeletion:
    def __init__(self, file_name):
        self.file_name = file_name
        # print(f"Getting page, line 446")
        self.file = pywikibot.Page(SITE, self.file_name)

        if not self.file_exists():
            raise NoPageError(
                self.file,
                "'%s' does not exists or was recently deleted" % self.file_name,
            )

        self.latest_revision_time = [
            revdata.timestamp for revdata in self.file.revisions(reverse=False, total=1)
        ][0]

        self.latest_revision_sha1 = [
            revdata.sha1 for revdata in self.file.revisions(reverse=False, total=1)
        ][0]

        self.talk_page_name = "File_talk:" + self.file.title(with_ns=False)
        # print(f"Getting page, line 463")
        self.talk_page = pywikibot.Page(SITE, self.talk_page_name)
        self._uploader = self.uploader()

        self._deletion_category = self.deletion_category()
        self.category_md5_hash = hashlib.md5(
            self._deletion_category.encode("utf-8")
        ).hexdigest()

        self.nominator_and_nomination = NominatorAndNomination(
            self.file_name, self._deletion_category
        )
        self.nominator = self.nominator_and_nomination.nominator
        self.nomination_reason = self.nominator_and_nomination.nomination_reason
        self.nomination_time = self.nominator_and_nomination.nomination_time

        self.total_editors = self.file.contributors(total=100)
        self.uploader_is_nominator = self.has_uploader_requested_deletion()
        self.is_a_moved_file_redirect = self.is_moved_file()

    def __repr__(self):
        return (
            "\n-----\n FileName : "
            + str(self.file_name)
            + "\n Nominator : "
            + str(self.nominator)
            + "\n Uploader : "
            + str(self._uploader)
            + "\n UploaderIsNominator : "
            + str(self.uploader_is_nominator)
            + "\n Category : "
            + str(self._deletion_category)
            + "\n CategoryMD5Hash : "
            + str(self.category_md5_hash)
            + "\n MovedFileRedirect : "
            + str(self.is_a_moved_file_redirect)
            + "\n NominationTime : "
            + str(self.nomination_time)
            + "\n LastRevisionTime : "
            + str(self.latest_revision_time)
            + "\n LastRevisionSha1 : "
            + str(self.latest_revision_sha1)
            + "\n Reason : "
            + str(self.nomination_reason)
            + "\n-----"
        )

    def publish(self):
        def encrypt_data(data):
            cipher_suite = Fernet(config.KEY.encode())
            return cipher_suite.encrypt(str(data).strip().encode()).decode()

        value = {
            "file_name": encrypt_data(self.file_name),
            "nominator": encrypt_data(self.nominator),
            "uploader": encrypt_data(self._uploader),
            "uploader_is_nominator": encrypt_data(self.uploader_is_nominator),
            "deletion_category": encrypt_data(self._deletion_category),
            "is_a_moved_file_redirect": encrypt_data(self.is_a_moved_file_redirect),
            "nomination_time": encrypt_data(self.nomination_time),
            "latest_revision_time": encrypt_data(self.latest_revision_time),
            "latest_revision_sha1": encrypt_data(self.latest_revision_sha1),
            "nomination_reason": encrypt_data(self.nomination_reason),
        }

        key = self.category_md5_hash + "_" + self.latest_revision_sha1
        pubsub.setex(key, value)

    def has_uploader_requested_deletion(self):
        """
        Identify if the uploader nominated thier own upload for deletion.
        We should not notify the uploader if they want thier own upload
        deleted.

        We first create a list of all human editors and if there is only one
        human editor then we assume that the uploader wants thier own file
        deleted and return True.

        If there are zero human editors, it implies that the uploader is a bot
        and it's nominated it's own upload for deletion. Why? Maybe bugs.

        Finally we compare the values of upload and nominator and if they are
        same, and set the nomination reason to G7 if already not set and
        nomination time to the latest edit if not set as the data is from recent
        changes.
        """

        all_editors = list(self.total_editors.keys())
        human_editors = []

        for editor in all_editors:
            # print(f"Getting user, line 554")
            if "bot" not in pywikibot.User(SITE, editor).rights():
                human_editors.append(editor)

        if (len(human_editors)) <= 1:
            if not self.nomination_time:
                self.nomination_time = self.latest_revision_time

            if not self.nominator:
                self.nominator = self.uploader()

            if not self.nomination_reason or self.nomination_reason.isspace():
                self.nomination_reason = (
                    "[[Special:MyLanguage/COM:CSD#G7|CSD"
                    + " G7]] (Author or uploader request deletion)"
                )

            return True

        if self.uploader() == self.nominator:

            if not self.nomination_reason or self.nomination_reason.isspace():
                self.nomination_reason = (
                    "[[Special:MyLanguage/COM:CSD#G7|CSD"
                    + " G7]] (Author or uploader request deletion)"
                )

            if not self.nomination_time:
                # recent changes data
                self.nomination_time = self.latest_revision_time

            return True

        return False

    def is_moved_file(self):
        """
        Not really a file but a redirect on the file descriptor that is
        nominated for deletion by someone who does not want the redirect
        from the old file name intact.

        Grab the first revision of the file page and if tag "mw-new-redirect"
        is found return True else False.
        """
        for revdata in self.file.revisions(reverse=True, total=1):
            if "mw-new-redirect" in revdata.tags:
                return True
        return False

    def file_exists(self):
        """
        Some admin might be deleting stuff by looking at the recent changes
        or they are the nominator and want the file deleted and don't want to
        wait for an another admin. This method checks if the file is still not
        deleted.
        """
        return self.file.exists()

    def deletion_category(self):
        """
        The method is written correctly and with sanity.
        The reason I'm storing the file categories in found_cats
        is that we should priortize the speedydeletions over 7 days or regular
        deletions. deletion_categories is a list ordered keeping in mind this issue.
        If a file has 2 templates we wanna notify for the deletion
        which is supposed to take place sooner. Also we don't wanna notify for
        both the deletions as it might piss off some users.
        """

        found_cats = []

        for cat in self.file.categories():
            found_cats.append(cat.title(with_ns=False))

        for cat in deletion_categories:
            if cat in found_cats:
                return cat

    def uploader(self, link=False, obj=False):
        """Set the value of _uploader and returns the uploader name"""
        self._uploader = page_creator(self.file, link=link, obj=obj)
        return self._uploader


def main():
    file_nominated_for_deletion_name = "File:Gaime.play.jpg"
    # cat = "Category:Deletion requests September 2021"
    cat = None

    if cat:
        from pywikibot import pagegenerators
        gen = pagegenerators.CategorizedPageGenerator(pywikibot.Category(SITE, cat))
        for page in gen:
            file_nominated_for_deletion_name = page.title()

            print(file_nominated_for_deletion_name)

            file_nominated_for_deletion = FileNominatedForDeletion(
                file_nominated_for_deletion_name
            )

            print(repr(file_nominated_for_deletion))
            file_nominated_for_deletion.publish()
    else:
        file_nominated_for_deletion = FileNominatedForDeletion(
            file_nominated_for_deletion_name
        )

        print(repr(file_nominated_for_deletion))
        file_nominated_for_deletion.publish()


if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
