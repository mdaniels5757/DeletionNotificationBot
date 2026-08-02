#!/bin/bash
THRESHOLD=$(date -d 'now - 60 min' +%s)
FILE_1_TIME=$(date -r publisher.out +%s)
FILE_2_TIME=$(date -r publisher.err +%s)

if (( FILE_1_TIME <= THRESHOLD && FILE_2_TIME <= THRESHOLD )); then
        exit 1
fi
