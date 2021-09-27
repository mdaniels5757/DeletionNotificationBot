#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
eval "${parent_path}/venv/bin/python3 ${parent_path}/predeletion/notify_uploader.py -dir:\"${parent_path}\""
