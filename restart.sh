#!/bin/bash -x
toolforge jobs flush
toolforge jobs load jobs.yaml

#Misunderstood what SAL was for...
#read -p "Reason for restarting (used for logging): " REASON
#dologmsg Restarted all jobs because "\""$REASON"\""
