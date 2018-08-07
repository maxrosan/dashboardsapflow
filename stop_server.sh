#!/bin/sh

for i in `ps xau | grep "start_server.sh" | awk '{ print $2 }'`; do
  kill -9 $i || true
done;

for i in `ps xau | grep "server.py" | awk '{ print $2 }'`; do
  kill -9 $i || true
done;
