# MorphStore: Analytical Query Engine with a Holistic Compression-Enabled Processing Model

Patrick Damme, Annett Ungethüm, Johannes Pietrzyk, Alexander Krause, Dirk Habich, Wolfgang Lehner:
**MorphStore: Analytical Query Engine with a Holistic Compression-Enabled Processing Model.**
*Proc. VLDB Endow. 13(11)*: 2396-2410 (2020)

Open access via: [vldb.org](http://www.vldb.org/pvldb/vol13/p2396-damme.pdf) | arXiv.org (*coming soon*)

## Experiments of our VLDB 2020 paper

This repository contains
- the *code* needed to reproduce our experiments
- all *artifacts* produced in our evaluation

There are two kinds of experiments
- *micro benchmarks* (Section 5.1 in the paper)
- *Star Schema Benchmark* (Sections 5.2, 6, and 1 in the paper).

The source code in this repository can be used to conduct all experiments in the paper.
It includes MorphStore via git-submodules.
The source code of MorphStore itself can be found in the [Engine](https://github.com/MorphStore/Engine) and [Benchmarks](https://github.com/MorphStore/Benchmarks) repositories.

## System Requirements

**Operating system**

- GNU/Linux
  - we used a 64-bit Ubuntu 18.10 with Linux kernel 4.18.0-13-generic
  - we also tested a 64-bit Ubuntu 20.4.1 with Linux kernel 5.4.0-48-generic

**Software**

*For the micro benchmarks and the Star Schema Benchmark:*
- cmake (we tested 3.12, 3.13, and 3.16)
- make (we tested 4.1 and 4.2.1)
- g++ (we used 8.3.0 and also tested 8.1.0 and 8.4.0)
- numactl (we used it, and recommend it if you have a multi-socket system)

*Only for the Star Schema Benchmark:*
- python3 (we tested 3.5.2, 3.6.7, and 3.8.5)
- pandas (we used 0.24.2 and also tested 1.1.4)

*Only for the diagram generation:*
- matplotlib (we used 3.0.3 and also tested 3.3.3)
- seaborn (we used 0.9.0 and also tested 0.11.0)

**Hardware**
- an Intel processor supporting AVX-512
  - we used an Intel Xeon Gold 6130 (2.1 GHz, 32 KiB L1, 1 MiB L2, 22 MiB L3-cache)
- free disk space
  - about 134 GiB during the SSB data generation
  - about 102 GiB after the SSB data generation
  - this is because we derive several artifacts from the original SSB data and delete some of them during the process
- at least 68 GiB of free main memory (ideally on one socket)

## How to Obtain the Source Code

```bash
git clone --recursive https://github.com/MorphStore/VLDB-2020.git
```

We recommend to use `--recursive` to clone the git-submodules as well.

## How to Re-run the Entire Evaluation

```bash
numactl -m 0 -N 0 -- ./vldb2020_microbenchmarks.sh
numactl -m 0 -N 0 -- ./vldb2020_ssb.sh
```

We used numactl to ensure that all memory allocation and code execution happens on the same socket to exclude NUMA effects.
You can omit numactl at the risk of compromising the measurements.
Of course, you do not need numactl at all if you have a single-socket system.

The entire evaluation takes approximately 5 days on our system.
This is mostly due to the greedy search for the actual best/worst format combinations, which we use as baselines.
Everything but this greedy search takes about 18 hours.

## Micro Benchmarks

You can re-run the experiments in Section 5.1 by `numactl -m 0 -N 0 -- ./vldb_microbenchmarks.sh`.

### Steps

This script executes the following sequence of steps:

1. **compile (c)** *(about 2 minutes)*
  - compiles the executables for the micro benchmarks
2. **run (r)** *(about 1 hour)*
  - executes the micro benchmarks
3. **visualize (v)** *(a couple of seconds)*
  - generates the diagrams in the paper from the experiments' measurements

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

1. **setup (s)** *(about 2 minutes)*
  - downloads and compiles the SSB data generator
  - downloads and compiles MonetDB
2. **calibrate (c)** *(about 1 hour)*
  - compiles and executes the micro benchmarks for calibrating our cost model for lightweight integer compression algorithms in MorphStore
3. **generate (g)** *(about 4.5 days, about 4 hours without greedy search)*
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
4. **run (r)** *(about 12 hours)*
  - executes the SSB in MorphStore using different strategies to determine the compressed formats of the base columns and intermediates
  - executes the SSB in MonetDB on both instances (BIGINT and narrow)
5. **visualize (v)** (a couple of seconds)
  - generates the diagrams in the paper (Figures 1, 7, 8, 9, 10) from the experiments' measurements
  
### Arguments

Invoke `vldb2020_ssb.sh` without arguments to execute all steps using the parameters we used in our evaluation.

The script also offers some arguments (see `./vldb2020_ssb.sh --help` for details (*coming soon*)).
However, *note that not using the defaults might result in different experimental results than in the paper*, which would require thorough interpretation.

argument | default | other examples
--- | --- | ---
-s, --start | setup | setup, calibrate, generate, run, visualize
-e, --end | visualize | *see above*
-sf, --scaleFactor | 100 | 1, 10, 100, ...
-q, --queries | *all* | 1.1, "2.1 2.2 2.3"
-r, --repetitions | 10 | 1, 2, 3, ...
-g, --repetitionsGreedy | 3 | 1, 2, 3, ...
-ps, --processingStyle | avx512<v512<uint64_t>> | scalar<v64<uint64_t>>, sse<v128<uint64_t>>, avx2<v256<uint64_t>>

The `--start` and `--end` arguments can be used to control which steps to (re-)execute.
Furthermore, you can use the optional arguments `--withoutMorphStore` or `--withoutMonetDB` to **not** use the respective system.
This might be useful if you are not interested in one of them, or have dependency issues you don't want to fix right now.

Deviating from the defaults can allow you to
- execute the experiments on a processor not supporting AVX-512 (expect different results than in the paper)
- quickly execute the entire script to test/debug it, e.g. by `./vldb2020_ssb.sh -sf 1 -q 1.1 -r 1`
- or anything else experimental

## Generated Artifacts and Diagrams

All artifacts created by re-running the experiments are automatically stored in a directory `artifacts`.
The artifacts of our original evaluation can be found in the directory `artifacts_original`.

**Micro benchmarks**

The following artifacts can be found in `artifacts/microbenchmarks`:

- **diagrams for Figures 4, 5, and 6**: `figure*.pdf`
- CSV files for Figure 4: `example_#.csv`
- CSV files for Figure 5: `singleop_#.csv`
- CSV files for Figure 6: `simplequery_#.csv`

There are 10 instances of each CSV file, one per repetition of the experiment.

**Star Schema Benchmark**

The folllowing artifacts can be found in `artifacts/ssb`:

- **diagrams for Figures 1, 7, 8, 9, and 10**: `dias_sf100`
- runtimes of SSB queries in MorphStore: `times_MorphStore_sf100`
  - subdirectories for different format combinations, numbered due to ten repetitions
- runtimes of SSB queries in MonetDB: `times_MonetDB_sf100`
- best format combinations determined by greedy algorithm: `ssb_formats_bestperf_sf100`
- worst format combinations determined by greedy algorithm: `ssb_formats_worstperf_sf100`
- data characteristics of all base and intermediate columns: `dc_sf100`
- physical sizes of all base and intermediate columns: `size_sf100`
- SSB base data: `data_sf100` (41 GiB)
- profiles of compression algorithms for cost-based format selection: `compr_profiles`

Most of the directories contain one CSV file per SSB query.
Finally, two variants of the SSB base data are loaded into MonetDB.
These reside in `MonetDB/monetdbfarm` (43 GiB, 18 GiB).
