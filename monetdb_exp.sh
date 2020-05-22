#!/bin/bash

set -e

scaleFactor=10

cd MorphStore/Benchmarks/ssb

for intType in BIGINT tight
do
    ./monetdb_ssb.sh -sf $scaleFactor -r 12 -t BIGINT > ../../../monetdb_ssb_${intType}.csv #2> /dev/null
done

set +e