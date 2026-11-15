#!/bin/sh
# Print the process identity at startup. Do not print environment values.
echo "isolation: user=$(id -un)"
echo "isolation: uid=$(id -u)"
echo "isolation: gid=$(id -g)"
if [ -r /proc/self/status ]; then
  grep -E '^(CapEff|CapPrm|CapBnd):' /proc/self/status | while read -r line; do
    echo "isolation: $line"
  done
fi
echo "isolation: privileged=false"
