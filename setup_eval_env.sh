#!/bin/bash

# Abort if some step fails.
set -e


# 1. Create a directory for all source code and artifacts

mkdir MorphStore
cd MorphStore


# 2. Clone required MorphStore repositories

git clone https://github.com/MorphStore/Engine.git
git clone https://github.com/MorphStore/Benchmarks.git
git clone https://github.com/MorphStore/LC-BaSe.git


# 3. Obtain the Star Schema Benchmark data generator

git clone https://github.com/lemire/StarSchemaBenchmark.git
mv StarSchemaBenchmark ssb-dbgen


# 4. Generate the SSB base data

cd Benchmarks/ssb
./ssb.sh -e g -um s -sf 10


# 5. Check if things work for the purely uncompressed processing

# scalar execution
./ssb.sh -s t -um s -sf 10
# vectorized with AVX-512
./ssb.sh -s t -um s -sf 10 -ps "avx512<v512<uint64_t>>"


# 6. Produce all artifacts required for using compression

./prepare4compr.sh -sf 10 -maxps avx512 -r 1


set +e