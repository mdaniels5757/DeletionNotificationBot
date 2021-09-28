#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
cd "${parent_path}"
git pull
qstat
qdel pre_del_pub
jsub -once -quiet -N pre_del_pub bash "${parent_path}/start_pre_del_publisher.sh"
qdel pre_del_notify
jsub -once -quiet -N pre_del_notify bash "${parent_path}/start_pre_del_notify.sh"
qstat
