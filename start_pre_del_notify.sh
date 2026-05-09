#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
echo $parent_path
# eval "${parent_path}/venv/bin/python3 ${parent_path}/predeletion/prune.py"
# eval "${parent_path}/venv/bin/python3 ${parent_path}/predeletion/notify_uploader.py -dir:\"${parent_path}\""
# source /data/project/deletion-notification-bot-2/DeletionNotificationBot/venv/bin/activate
source "${parent_path}/venv/bin/activate"
pwb "${parent_path}/predeletion/prune.py"
pwb "${parent_path}/predeletion/notify_uploader.py" -dir:"${parent_path}"
