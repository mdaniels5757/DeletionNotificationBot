#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "${parent_path}"
/data/project/deletion-notification-bot-2/.local/bin/uv run predeletion/run_publisher.py
