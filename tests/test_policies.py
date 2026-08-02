from datetime import date

from models import DeletionNomination
from policies import POLICIES, SIGNATURE, categories_for, render_notice


def item(category, reason="Reason"):
    return DeletionNomination(
        "File:One.jpg",
        "Nominator",
        "Uploader",
        "False",
        category,
        "False",
        "n",
        "l",
        "a" * 40,
        reason,
    )


def test_registry_has_all_prioritized_categories():
    categories = categories_for(date(2026, 8, 2))
    assert len(categories) == 8
    assert categories[:4] == [
        "Advertisements for speedy deletion",
        "Copyright violations",
        "Other speedy deletions",
        "Personal files for speedy deletion",
    ]


def test_each_policy_renders_first_notice_and_standard_nominator():
    for policy in POLICIES:
        category = policy.category(date(2026, 8, 2))
        reason = (
            "REASON:|###x###-SUBPAGE:###Example###"
            if policy.needs_subpage
            else "Reason"
        )
        text = render_notice(policy, [item(category, reason)])
        assert "File:One.jpg" in text
        assert "{{Noping|Nominator}}" in text


def test_grouped_notice_preserves_and_also_detail():
    policy = POLICIES[1]
    category = policy.category(date(2026, 8, 2))
    text = render_notice(policy, [item(category), item(category, "Second reason")])
    assert "And also:" in text
    assert "Reason : Second reason" in text
    assert SIGNATURE.startswith("\nI'm a computer program")
