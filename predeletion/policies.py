"""Deletion-category policy and notification rendering.

This is intentionally the one place to extend when Commons adds a category.
"""

from dataclasses import dataclass
from datetime import date
import re
from typing import Callable

STANDARD_NOMINATOR = (
    "\n<p style=\"font-family:'Stencil Std'\">\nUser who nominated the file for deletion "
    "(Nominator) : {{Noping|%s}}.</p>"
)

HOTWORDS = {
    "ads": ("{{SD|G10}}", "G10", "spam"),
    "copyvio": ("{{copyvio", "Possible copyright violation", "Marking as possible copyvio", "{{logo", "db-copyvio", "{{SD|F3}}"),
    "speedy": ("{{SD", "{{Speedydelete|", "{{speedy|", "Requesting speedy deletion", "{{speedydeletion", "{{csd", "spd|f10", "db-g7", "SD|1=G7", "g7", "{{speedy", "{{db"),
    "personal": ("{{SD|F10", "{{Selfie", "noncontributor", "personal file", "non-contributors", "personal image", "{{SDF10", "F10", "SDF10"),
    "dr": ("{{delete|reason=", "[[COM:DR|Nominating for deletion]]", "{{delete|", "Nominating for deletion"),
    "license": ("AntiCompositeBot/NoLicense/tag", "No license found, tagging with", "{{No license since"),
    "permission": ("No permission since", "Missing [[COM:PERMISSION|permission]]", "Missing permission", "since|month=", "no permission"),
    "source": ("This is a [[COM:DW|derivative work]] and no source or permission of the original work is provided", "{{dw no source since", "derivative work", "no source or permission", "{{No source since", "no source"),
}
SIGNATURE = (
    "\nI'm a computer program; please don't ask me questions but ask the user who "
    "nominated your file(s) for deletion (shown above) or at our "
    "[[Commons:Help_desk|Help Desk]]. //~~~~"
)


@dataclass(frozen=True)
class CategoryPolicy:
    key: str
    category: Callable[[date], str]
    hotwords: tuple[str, ...]
    first_notice: Callable[[object, str | None], str]
    detail: Callable[[object, str | None], str]
    needs_subpage: bool = False


def _fixed(name: str) -> Callable[[date], str]:
    return lambda _: name


def _notice(template: str) -> Callable[[object, str | None], str]:
    return lambda item, _: template % tuple([item.file_name] * template.count("%s"))


def _reason_detail(item: object, _: str | None) -> str:
    return "Reason : %s" % item.nomination_reason


def _dr_notice(item: object, subpage: str | None) -> str:
    return "\n{{subst:idw|1=%s|2=%s}}" % (item.file_name, subpage)


def _dr_detail(_: object, subpage: str | None) -> str:
    return "Entry page : [[Commons:Deletion requests/%s]]" % subpage


POLICIES = (
    CategoryPolicy("ads", _fixed("Advertisements for speedy deletion"), HOTWORDS["ads"], _notice("\n\n== [[:%s]] ==\n{{User:Deletion Notification Bot/NOADS/headingless|1=%s}}"), _reason_detail),
    CategoryPolicy("copyvio", _fixed("Copyright violations"), HOTWORDS["copyvio"], lambda item, _: "\n\n{{subst:Copyvionote|1=%s|2=%s|3=}} " % (item.file_name, item.nomination_reason), _reason_detail),
    CategoryPolicy("speedy", _fixed("Other speedy deletions"), HOTWORDS["speedy"], lambda item, _: "\n\n== [[:%s]] ==\n{{User:Deletion Notification Bot/SDEL/headingless|1=%s|2=%s}}" % (item.file_name, item.file_name, item.nomination_reason), _reason_detail),
    CategoryPolicy("personal", _fixed("Personal files for speedy deletion"), HOTWORDS["personal"], _notice("\n\n== [[:%s]] ==\n{{User:Deletion Notification Bot/personalNO/headingless|1=%s}}"), _reason_detail),
    CategoryPolicy("dr", lambda day: "Deletion requests %s" % day.strftime("%B %Y"), HOTWORDS["dr"], _dr_notice, _dr_detail, True),
    CategoryPolicy("license", lambda day: "Media without a license as of %s" % day.strftime("%-d %B %Y"), HOTWORDS["license"], _notice("\n{{subst:image license|1=%s}}"), _reason_detail),
    CategoryPolicy("permission", lambda day: "Media missing permission as of %s" % day.strftime("%-d %B %Y"), HOTWORDS["permission"], _notice("\n{{subst:image permission|1=%s}}"), _reason_detail),
    CategoryPolicy("source", lambda day: "Media without a source as of %s" % day.strftime("%-d %B %Y"), HOTWORDS["source"], _notice("\n{{subst:Image source |1=%s}}"), _reason_detail),
)


def category_policies(day: date) -> dict[str, CategoryPolicy]:
    return {policy.category(day): policy for policy in POLICIES}


def categories_for(day: date) -> list[str]:
    return [policy.category(day) for policy in POLICIES]


def find_policy(category: str, day: date) -> CategoryPolicy | None:
    for policy in POLICIES:
        if category == policy.category(day):
            return policy
    return None


def parse_deletion_request_reason(reason: str) -> tuple[str, str]:
    match = re.search(r"^REASON:\|###(.*?)###-SUBPAGE:###(.*?)###$", reason)
    if not match:
        raise ValueError("Invalid deletion-request notification reason")
    return match.group(1), match.group(2)


def render_notice(policy: CategoryPolicy, nominations: list[object]) -> str:
    """Render the legacy grouped talk-page text, excluding its edit summary."""
    notice = ""
    for index, item in enumerate(nominations, 1):
        subpage = parse_deletion_request_reason(item.nomination_reason)[1] if policy.needs_subpage else None
        if index == 1:
            notice += policy.first_notice(item, subpage)
            notice += STANDARD_NOMINATOR % item.nominator
        else:
            if index == 2:
                notice += "\nAnd also:"
            detail = policy.detail(item, subpage)
            notice += "\n* [[:%s]] <span style=\"font-family:'Stencil Std'\">( Nominator : {{Noping|%s}}  &#124;  %s )</span>" % (item.file_name, item.nominator, detail)
    return notice


def edit_summary(category: str, nominations: list[object]) -> str:
    first = nominations[0].file_name
    extra = "and %d other file(s)" % (len(nominations) - 1) if len(nominations) > 1 else " "
    return "Impending deletion notification - [[Category:%s|%s]] - [[:%s]] %s" % (category, category, first, extra)
