#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
eval "${parent_path}/venv/bin/python3 ${parent_path}/predeletion/run_publisher.py -dir:\"${parent_path}\""
