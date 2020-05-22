#!/bin/bash

set -e

cd MorphStore/Benchmarks/ssb

for intType in BIGINT tight
do
    ./ssb.sh -e g -sf 10 -mit $intType
done

set +e