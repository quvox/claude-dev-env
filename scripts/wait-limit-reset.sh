#!/bin/bash

if [ -z "$1" ]; then
	echo "usage: $0 HH:MM" >&2
	echo "error: 待機する時刻を HH:MM 形式で指定してください" >&2
	exit 1
fi

time="$1"

target=$(date -d "today $time" +%s)

now=$(date +%s)

if (( target <= now )); then

	  target=$(date -d "tomorrow $time" +%s)

fi

echo "** waiting until ${time}"
sleep $(( target - now ))
echo "FIRE!!!"
tmux send-keys -t :1 "go on" Enter
