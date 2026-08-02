"""Backward-compatible hotword exports.

New code should use :mod:`policies`; it keeps each category's complete policy
in one registry.
"""

from policies import HOTWORDS

advertisements_speedy_deletion_hot_words = list(HOTWORDS["ads"])
copyright_violations_hot_words = list(HOTWORDS["copyvio"])
other_speedy_deletions_hot_words = list(HOTWORDS["speedy"])
personal_files_for_speedy_deletion_hot_words = list(HOTWORDS["personal"])
deletion_requests_hot_words = list(HOTWORDS["dr"])
media_without_a_license_hot_words = list(HOTWORDS["license"])
media_missing_permission_hot_words = list(HOTWORDS["permission"])
media_without_a_source_hot_words = list(HOTWORDS["source"])
