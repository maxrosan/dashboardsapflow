#!/bin/sh

PIDs=`ps xau | grep "server.py" | awk '{ print $2 }'`

for i in $PIDs; do
  kill -9 $i || true
done;
