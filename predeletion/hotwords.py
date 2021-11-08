"""
Hot words are used to identify the revision that nominated a file for deletion.

What are hotwords? They are parts of the deletion templates and parts of standard
comments made by semi-automated scripts used by users.
"""

advertisements_speedy_deletion_hot_words = [
    "{{SD|G10}}",
    "G10",
    "spam",
]

copyright_violations_hot_words = [
    "{{copyvio",
    "Possible copyright violation",
    "Marking as possible copyvio",
    "{{logo",
    "db-copyvio",
    "{{SD|F3}}",
]

other_speedy_deletions_hot_words = [
    "{{SD",
    "{{Speedydelete|",
    "{{speedy|",
    "Requesting speedy deletion",
    "{{speedydeletion",
    "{{csd",
    "spd|f10",    
    "db-g7",
    "SD|1=G7",
    "g7",
    "{{speedy", 
    "{{db",
]

personal_files_for_speedy_deletion_hot_words = [
    "{{SD|F10",
    "{{Selfie", 
    "noncontributor",
    "personal file",
    "non-contributors",
    "personal image",
    "{{SDF10",
    "F10",
    "SDF10",
]

deletion_requests_hot_words = [
    "{{delete|reason=",
    "[[COM:DR|Nominating for deletion]]",
    "{{delete|",
    "Nominating for deletion",
]

media_without_a_license_hot_words = [
    "AntiCompositeBot/NoLicense/tag",
    "No license found, tagging with",
    "{{No license since",
]

media_missing_permission_hot_words = [
    "No permission since",
    "Missing [[COM:PERMISSION|permission]]",
    "Missing permission",
    "since|month=",
    "no permission",
]

media_without_a_source_hot_words = [
    "This is a [[COM:DW|derivative work]] and no source or permission of the original work is provided",
    "{{dw no source since",
    "derivative work",
    "no source or permission",
    "{{No source since",
    "no source",
]
