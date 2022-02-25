#!/usr/bin/env zsh

while [[ `cpuload` -gt "$1" ]]; do
	 sleep 30
done; ~/etc/script/notify_slack.sh "Heavy process finished"
