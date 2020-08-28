# MorphStore: Analytical Query Engine with a Holistic Compression-Enabled Processing Model

Patrick Damme, Annett Ungethüm, Johannes Pietrzyk, Alexander Krause, Dirk Habich, Wolfgang Lehner:
**MorphStore: Analytical Query Engine with a Holistic Compression-Enabled Processing Model.**
*Proc. VLDB Endow. 13(11)*: 2396-2410 (2020)

Open access via: [vldb.org](http://www.vldb.org/pvldb/vol13/p2396-damme.pdf) | arXiv.org (*coming soon*)

## Experiments of our VLDB 2020 paper

This repository contains
- the *code* needed to reproduce our experiments (so far partly, to be finished soon)
- all *artifacts* produced in our evaluation (coming soon)

There are two kinds of experiments
- *micro benchmarks* (Section 5.1 in the paper)
- *Star Schema Benchmark* (Sections 5.2, 6, and 1 in the paper).

**We are currently setting up this repository. Expect everything to be complete within the next couple of days.**

The source code of MorphStore itself is already open-source: Check out our [Engine](https://github.com/MorphStore/Engine) and [Benchmarks](https://github.com/MorphStore/Benchmarks) repositories.

## System Requirements

**Operating system**

- GNU/Linux (we used Ubuntu 18.10 with Linux kernel 4.18.0-13-generic)

**Software**

*For the micro benchmarks and the Star Schema Benchmark:*
- cmake (we tested 3.12 and 3.13)
- make (we tested 4.1 and 4.2.1)
- g++ (we used 8.3.0 and also tested 8.1.0)
- numactl (optional)

*Only for the Star Schema Benchmark:*
- python3 (we tested 3.5.2 and 3.6.7)
- pandas (we tested 0.24.2)

**Hardware** (*to be stated more precisely*)
- an Intel processor supporting AVX-512
- about 200 GB of free disk space for the SSB base data (and some artifacts derived from it) at scale factor 100
- at least 96 GB of main memory (ideally per socket)

## To Re-run the Entire Evaluation

```bash
numactl -m 0 -N 0 -- ./vldb2020_microbenchmarks.sh
numactl -m 0 -N 0 -- ./vldb2020_ssb.sh
```

We used numactl to ensure that all memory allocation and code execution happens on the same socket to exclude NUMA effects.
You can omit numactl at the risk of compromising the measurements.

## Micro Benchmarks

You can re-run the experiments in Section 5.1 by `numactl -m 0 -N 0 -- ./vldb_microbenchmarks.sh`.

### Steps

This script executes the following sequence of steps:

1. **compile (c)**: compiles the executables for the micro benchmarks
2. **run (r)**: executes the micro benchmarks
3. **visualize (v)**: generates the diagrams in the paper from the experiments' measurements

### Arguments

Invoke `vldb2020_microbenchmarks.sh` without arguments to execute all steps using the parameters we used in our evaluation.

The script also offers some arguments (see `./vldb2020_microbenchmarks.sh --help` for details (*coming soon*)).
However, *note that not using the defaults might result in different experimental results than in the paper*, which would require thorough interpretation.

argument | default | other examples
--- | --- | ---
-s, --start | compile | compile, run, visualize
-e, --end | visualize | *see above*
-r, --repetitions | 10 | 1, ...
-ps, --processingStyle | avx512<v512<uint64_t>> | scalar<v64<uint64_t>>, sse<v128<uint64_t>>, avx2<v256<uint64_t>>

The `--start` and `--end` arguments can be used to control which steps to (re-)execute.
Furthermore, you can use the optional arguments `--onlyExample`, `--onlySingleOp`, or `--onlySimpleQuery` to reproduce each of the three parts of the micro benchmarks in the paper separately.

## Star Schema Benchmark (SSB)

You can re-run the experiments in Sections 5.2, 6, and 1 in the paper by `numactl -m 0 -N 0 -- ./vldb2020_ssb.sh`.

### Steps

This script executes the following sequence of steps:

1. **setup (s)**
  - downloads and compiles the SSB data generator
  - downloads and compiles MonetDB
2. **calibrate (c)**
  - compiles and executes the micro benchmarks for calibrating our cost model for lightweight integer compression algorithms in MorphStore
3. **generate (g)**
  - generates the raw base data
  - applies dictionary coding to all non-integer columns
  - prepares base column files for use in MorphStore
  - loads base data into MonetDB
    - one instance with all columns of type BIGINT
    - one instance with each column of the narrowest possible integer type
  - derives some artifacts required for the evaluation
    - data characteristics of all base and intermediate columns
    - compressed sizes of all base and intermediate columns in all compressed formats currently supported
    - best and worst combinations of the base and intermediate columns' formats (greedy algorithm mentioned in the paper)
4. **run (r)**
  - executes the SSB in MorphStore using different strategies to determine the compressed formats of the base columns and intermediates
  - executes the SSB in MonetDB on both instances (BIGINT and narrow)
5. **visualize (v)**
  - generates the diagrams in the paper from the experiments‘ measurements
  - *coming soon!*
  
### Arguments

Invoke `vldb2020_ssb.sh` without arguments to execute all steps using the parameters we used in our evaluation.

The script also offers some arguments (see `./vldb2020_ssb.sh --help` for details (*coming soon*)).
However, *note that not using the defaults might result in different experimental results than in the paper*, which would require thorough interpretation.

argument | default | other examples
--- | --- | ---
-s, --start | setup | setup, calibrate, generate, run, visualize
-e, --end | visualize | *see above*
-sf, --scaleFactor | 100 | 1, 10, ...
-q, --queries | *all* | 1.1, "2.1 2.2 2.3"
-r, --repetitions | 10 | 1, ...
-ps, --processingStyle | avx512<v512<uint64_t>> | scalar<v64<uint64_t>>, sse<v128<uint64_t>>, avx2<v256<uint64_t>>

The `--start` and `--end` arguments can be used to control which steps to (re-)execute.
Furthermore, you can use the optional arguments `--withoutMorphStore` or `--withoutMonetDB` to **not** use the respective system.
This might be useful if you are not interested in one of them, or have dependency issues you don't want to fix right now.

Deviating from the defaults can allow you to
- execute the experiments on a processor not supporting AVX-512 (expect different results than in the paper)
- quickly execute the entire script to test/debug it, e.g. by `./vldb2020_ssb.sh -sf 1 -q 1.1 -r 1`
- or anything else experimental

## Generated Artifacts

*Description coming soon!*
