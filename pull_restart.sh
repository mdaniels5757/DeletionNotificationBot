#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "${parent_path}"
git fetch --all
git reset --hard origin/main
qstat
qdel pre_del_pub
qdel pre_del_notify
sleep 30
jsub -once -quiet -N pre_del_pub bash "${parent_path}/start_pre_del_publisher.sh"
jsub -once -quiet -N pre_del_notify bash "${parent_path}/start_pre_del_notify.sh"
qstat
