#!/bin/bash
cd /service/vfc/gvnfm/vnflcm/lcm
./run.sh

while [ ! -f logs/gvnfm_vnflcm.log ]; do
    sleep 1
done
tail -F logs/gvnfm_vnflcm.log
