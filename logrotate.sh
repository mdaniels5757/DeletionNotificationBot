#!/bin/bash
fsize_max=$((2 ** 28)) # 256MiB
files=('notifier.err' 'notifier.out' 'publisher.err' 'publisher.out' 'DeletionNotificationBot/logs/commands.log')
for f in "${files[@]}"; do
    fsize=$(stat -c%s "$f")
    if (( fsize >= fsize_max )); then
        savelog -c 30 "$f"
    fi
done
