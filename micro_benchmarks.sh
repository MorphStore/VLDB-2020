#!/bin/bash

# Abort if some step fails.
set -e


# 1. Change into the Engine repository

cd Engine


# 2. Build the executables for the micro benchmarks

./build.sh -noSelfManaging -hi -j2 -mon -avx512 -bMbm --target "select_benchmark_2_t select_sum_benchmark"


# 3. Run the micro benchmarks

build/src/microbenchmarks/select_benchmark_2_t > select_benchmark.csv
build/src/microbenchmarks/select_sum_benchmark > select_sum_benchmark.csv


set +e