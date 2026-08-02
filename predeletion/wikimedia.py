"""Pywikibot adapter kept at the application edge."""

from datetime import datetime, timezone, date
import re

import pywikibot

from models import DeletionNomination
from policies import categories_for, find_policy, parse_deletion_request_reason
from utils import commit, page_creator, revision_that_added_the_text_first


COPYVIO_REASONS = {
    "f1": "[[Commons:Criteria_for_speedy_deletion#F1|Apparent copyright violation]]",
    "f2": "[[Commons:Criteria_for_speedy_deletion#F2|Fair use content]]",
    "f3": "[[Commons:Criteria_for_speedy_deletion#F3|Derivative work of non-free content]]",
    "f4": "[[Commons:Criteria_for_speedy_deletion#F4|Failed license review]]",
    "f5": "[[Commons:Criteria_for_speedy_deletion#F5|Missing essential information]]",
    "f6": "[[Commons:Criteria_for_speedy_deletion#F6|License laundering]]",
    "f7": "[[Commons:Criteria_for_speedy_deletion#F7|File is empty, corrupt, or in a disallowed format]]",
    "f8": "[[Commons:Criteria_for_speedy_deletion#F8|Exact or scaled-down duplicate]]",
    "f9": "[[Commons:Criteria_for_speedy_deletion#F9|The file contains additional embedded data in the form of a password protected archive.]]",
    "f10": "[[Commons:Criteria_for_speedy_deletion#F10|Personal photos by non-contributors]]",
}
CSD_REASONS = {
    str(n): "[[Special:MyLanguage/COM:CSD#G%s|CSD G%s]] (%s)" % (n, n, reason)
    for n, reason in {
        1: "Test page, accidental creation, or page containing nonsense or no valid content",
        2: "Unused and implausible, or broken redirect",
        3: "Content intended as vandalism, threat, or attack",
        4: "Recreation of content previously deleted per community consensus",
        5: "Temporary deletion for history cleaning or revision suppression",
        6: "Uncontroversial maintenance",
        7: "Author or uploader request deletion",
        8: "Page dependent on deleted or non-existent content",
        9: "Wikimedia Foundation office action",
        10: "Files and pages created as advertisements",
        11: "Blatant text copyright violation",
    }.items()
}


class WikimediaGateway:
    def __init__(self, site):
        self.site = site

    def category_for(self, page: pywikibot.Page, day: date) -> str | None:
        found = {category.title(with_ns=False) for category in page.categories()}
        return next(
            (category for category in categories_for(day) if category in found), None
        )

    def nomination_details(
        self, file_name: str, category: str, page: pywikibot.Page, day: date
    ) -> tuple[str | None, str | None, str]:
        policy = find_policy(category, day)
        revision = revision_that_added_the_text_first(
            self.site, file_name, policy.hotwords
        )
        if revision and revision.user and revision.timestamp:
            return (
                revision.user,
                revision.timestamp,
                self.reason_for(policy.key, file_name, page),
            )
        else:
            return None, None, self.reason_for(policy.key, file_name, page)

    def reason_for(self, key: str, file_name: str, page: pywikibot.Page) -> str:
        if key == "ads":
            return "[[Special:MyLanguage/COM:CSD#G10|CSD G10]] (files and pages created as advertisements)"
        if key == "personal":
            return "[[Special:MyLanguage/COM:CSD#F10|CSD F10]] (personal photos by non-contributors)"
        if key == "license":
            return "This media file does not have sufficient information on its copyright status. If you have created this file yourself, or the file is in the public domain, you can edit the file description page to license it under one of the allowed licenses."
        if key == "permission":
            return "This media file is missing evidence of permission."
        if key == "source":
            return "This media file is a derivative work incorporating another work or works. While the source of this file has been identified, essential source information for all work incorporated in this file is missing."
        text = page.get()
        if key == "copyvio":
            return self._copyvio_reason(text)
        if key == "speedy":
            return self._speedy_reason(text)
        return self._deletion_request_reason(file_name, page, text)

    @staticmethod
    def _copyvio_reason(text):
        text = re.sub(
            r"\(\[\[User talk:(?:.*?)\|<span class=\"signature(?:.*)\(UTC\)", " ", text
        )
        match = re.search(r"{{(?:\s*?|)(?:db\-|)[Cc]opyvio(?:\s*?|)\|(.*?)}}", text)
        if match:
            reason = (
                match.group(1)
                .replace("1=", " ")
                .replace("source=", " ")
                .replace("|", " ")
            )
        else:
            lower = text.lower()
            reason = (
                "File is not a freely licensed logo"
                if re.search(r"{{(?:\s*?|)logo(.*?)}}", text)
                else next(
                    (
                        value
                        for code, value in COPYVIO_REASONS.items()
                        if "{{sd|" + code in lower
                    ),
                    "Copyright infringement / piracy" if "{{copyvio}}" in lower else "",
                )
            )
        return re.sub(r"[Cc]ategory:", ":Category:", reason)

    @staticmethod
    def _speedy_reason(text):
        for code, reason in CSD_REASONS.items():
            if re.search(
                r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|)"
                + code
                + r"(?:\s*?|)}}",
                text,
            ):
                return reason
        for pattern in (
            r"{{(?:\s*?|)(?:[Ss][Dd]|[Dd]b-g)(?:\s*?|)(?:\||)(?:\s*?|)(?:[Gg]|1=[Gg])[0-9]{1,2}(?:\s*?|)(?:\|2=|)(.*?)}}",
            r"{{(?:\s*?|)(?:[Ss]peedy|[Cc]sd|SD\|1=G7|2=|[Dd]b\-g7|[Ss]peedy\s*?[Dd]elet(?:e|ion))(?:\s*?|)\|(.*?)}}",
        ):
            match = re.search(pattern, text)
            if match:
                return re.sub(
                    r"[Cc]ategory:",
                    ":Category:",
                    match.group(1)
                    .replace("1=", " ")
                    .replace("2=", " ")
                    .replace("|", " "),
                )
        return None

    def _deletion_request_reason(self, file_name, page, text):
        subpage_match = re.search(
            r"{{(?:\s*?|)[Dd]elete(?:\s*?|)(?:.*?)\|subpage=(.*?)\|(?:.*?)}}", text
        )
        reason_match = re.search(
            r"{{(?:\s*?|)[Dd]elete(?:\s*?|)(?:.*?)\|reason=(.*?)\|(?:.*?)}}", text
        )
        subpage = subpage_match.group(1).strip() if subpage_match else None
        if not subpage:
            for backlink in page.backlinks(follow_redirects=True, namespaces=4):
                title = backlink.title()
                if (
                    "Commons:Deletion requests/" not in title
                    or "Commons:Deletion requests/%s"
                    % datetime.now(tz=timezone.utc).strftime("%Y")
                    in title
                ):
                    continue
                if file_name.replace(" ", "_") in pywikibot.Page(
                    self.site, title
                ).get().replace(" ", "_"):
                    subpage = title.replace("Commons:Deletion requests/", "")
        return "REASON:|###%s###-SUBPAGE:###%s###" % (
            reason_match.group(1).strip() if reason_match else "REASONNOTFOUND",
            subpage or "CANNOTFINDTHESUBPAGE",
        )

    def build_nomination(self, file_name: str, day: date) -> DeletionNomination:
        page = pywikibot.Page(self.site, file_name)
        if not page.exists():
            raise pywikibot.exceptions.NoPageError(
                page, "%s does not exist" % file_name
            )
        category = self.category_for(page, day)
        if category is None:
            raise ValueError("%s is not in a supported deletion category" % file_name)
        latest: pywikibot.page.Revision = next(page.revisions(reverse=False, total=1))
        nominator, nominated_at, reason = self.nomination_details(
            file_name, category, page, day
        )
        uploader = page_creator(page)
        editors = list(page.contributors(total=100).keys())
        human = [
            name
            for name in editors
            if "bot" not in pywikibot.User(self.site, name).rights()
        ]
        own = len(human) <= 1 or uploader == nominator
        if own:
            nominator, nominated_at = (
                nominator or uploader,
                nominated_at or latest.timestamp,
            )
            reason = reason or CSD_REASONS["7"]
        moved = any(
            "mw-new-redirect" in revision.tags
            for revision in page.revisions(reverse=True, total=1)
        )
        return DeletionNomination(
            file_name=file_name,
            nominator=nominator if nominator is not None else "Unknown nominator",
            uploader=uploader,
            uploader_is_nominator=own,
            deletion_category=category,
            is_a_moved_file_redirect=moved,
            nomination_time=nominated_at or "Unknown nomination time",
            latest_revision_time=latest.timestamp,
            latest_revision_sha1=latest.sha1,
            nomination_reason=reason,
        )

    def is_notifiable(self, nomination, needs_subpage=False):
        if (
            nomination.is_a_moved_file_redirect == "True"
            or nomination.nominator == nomination.uploader
            or nomination.nominator == "AntiCompositeBot"
        ):
            return False
        talk = pywikibot.Page(self.site, "User_talk:%s" % nomination.uploader)
        if talk.isRedirectPage():
            talk = talk.getRedirectTarget()
        text = talk.get().replace(" ", "_").lower()
        if nomination.file_name.replace(" ", "_").lower() in text:
            return False
        if needs_subpage:
            _, subpage = parse_deletion_request_reason(nomination.nomination_reason)
            if subpage.replace(" ", "_").lower() in text:
                return False
            page = pywikibot.Page(
                self.site, "Commons:Deletion requests/" + subpage.strip()
            )
            if (
                page.exists()
                and nomination.file_name.replace(" ", "_").lower()
                in page.get().replace(" ", "_").lower()
                and nomination.uploader in page.contributors(total=100).keys()
            ):
                return False
        return True

    def submit(self, uploader, notice, summary):
        page = pywikibot.Page(self.site, "User_talk:%s" % uploader)
        old_text = page.get()
        commit(old_text, old_text + notice, page, summary)
