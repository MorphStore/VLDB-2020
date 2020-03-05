# MorphStore: Analytical Query Engine with a Holistic Compression-Enabled Processing Model
## Experiments of our VLDB 2020 submission

This repository contains all necessary instructions, scripts, etc. to reproduce the evaluation of our recent submission to VLDB 2020.

**We are currently setting up this repository. Expect everything to be complete within the next couple of days.**

The source code of MorphStore itself is already open-source: Check out our [Engine](https://github.com/MorphStore/Engine) and [Benchmarks](https://github.com/MorphStore/Benchmarks) repositories.

## System Requirements

Your system should fulfill the following requirements to reproduce our evaluation:

**Operating system**

- GNU/Linux (we used Ubuntu 18.10 with Linux kernel 4.18.0-13-generic)

**Software**

*For the micro benchmarks and the Star Schema Benchmark:*
- cmake (we tested 3.12 and 3.13)
- make (we tested 4.1 and 4.2.1)
- g++ (we used 8.3.0 and also tested 8.1.0)

*Only for the Star Schema Benchmark:*
- python3 (we tested 3.5.2 and 3.6.7)
- pandas (we tested 0.24.2)

**Hardware**
- an Intel processor supporting AVX-512
- about 20 GB of free disk space for the SSB base data (and some artifacts derived from it) at scale-factor 10
- at least 16 GB of main memory

## Setting up the Evaluation Environment

Note that you can automatically run all of the steps explained below by using `./setup_eval_env.sh`.

1. **Create a directory for all source code and artifacts**
   
   Let's call this directory `MorphStore` and change into it:

   ```bash
   mkdir MorphStore
   cd MorphStore
   ```
   
2. **Clone required MorphStore repositories**
   
   MorphStore consists of a couple of individual repositories.
   Here, we need to clone three of them: [Engine](https://github.com/MorphStore/Engine) (MorphStore's holistic compression-enabled query execution engine), [Benchmarks](https://github.com/MorphStore/Benchmarks) (scripts and artifacts for running SSB), and [LC-BaSe](https://github.com/MorphStore/LC-BaSe) (our cost-model for lightweight integer compression algorithms).
   
   ```bash
   git clone https://github.com/MorphStore/Engine.git
   git clone https://github.com/MorphStore/Benchmarks.git
   git clone https://github.com/MorphStore/LC-BaSe.git
   ```
   
*If you only want to reproduce the micro benchmarks, you can actually stop the setup here.*
   
3. **Obtain the Star Schema Benchmark data generator**
   
   We recommend to use the [StarSchemaBenchmark](https://github.com/lemire/StarSchemaBenchmark) repository provided by Daniel Lemire.
   
   ```bash
   git clone https://github.com/lemire/StarSchemaBenchmark.git
   mv StarSchemaBenchmark ssb-dbgen
   ```
   
4. **Generate the SSB base data**

   This includes (i) the compilation of the SSB data generator, (ii) the SSB base data generation, and (iii) the dictionary encoding of the generated data.
   This setup step has not been optimized for performance, it may take about 20 minutes.
   
   ```bash
   cd Benchmarks/ssb
   ./ssb.sh -e g -um s -sf 10
   ```
   
5. **Check if things work for the purely uncompressed processing**
   
   Let's execute all SSB queries on purely uncompressed data.
   First with a scalar execution.
   
   ```bash
   ./ssb.sh -s t -um s -sf 10
   ```
   
   Then, vectorized with AVX-512.
   
   ```bash
   ./ssb.sh -s t -um s -sf 10 -ps "avx512<v512<uint64_t>>"
   ```
   
   In both cases, in the end, you should see the following:
   
   ```
   ssb q1.1: good
   ssb q1.2: good
   ssb q1.3: good
   ssb q2.1: good
   ssb q2.2: good
   ssb q2.3: good
   ssb q3.1: good
   ssb q3.2: good
   ssb q3.3: good
   ssb q3.4: good
   ssb q4.1: good
   ssb q4.2: good
   ssb q4.3: good
   ```
   
   If the output says `BAD` for some query, then something went wrong, which should actually not be the case...
   
4. **Produce all artifacts required for using compression**
   
   This includes (i) the analysis of the data characteristics of all base columns and intermediates, (ii) exhaustively finding out the physical size of all base and intermediate columns in all compressed formats, and (iii) the calibration of our cost model for lightweight integer compression algorithms.
   Not all of these things are needed for all compression-related features of MorphStore, however, for simplicity of explanation, we do all these things here.
   Again, this setup step has not been optimized for performance, it may take about 40 minutes.
   
   ```bash
   ./prepare4compr.sh -sf 10 -maxps avx512 -r 1
   ```

## Reproducing the Micro Benchmark Experiments

Here, we assume that your present working directory is `VLDB-2020` and that it contains the directory `MorphStore` created by the setup steps above.
Note that you can automatically run all of the steps explained below by using `./micro_benchmarks.sh`.

1. **Change into the Engine repository**
   
   ```bash
   cd Engine
   ```

2. **Build the executables for the micro benchmarks**

   This is done using MorphStore's build script.
   
   ```bash
   ./build.sh -noSelfManaging -hi -j2 -mon -avx512 -bMbm --target "select_benchmark_2_t select_sum_benchmark"
   ```
   
3. **Run the micro benchmarks**

   The evaluation results are written to the files `select_benchmark.csv` and `select_sum_benchmark.csv`.
   Note that the following commands run each benchmark only once (in our evaluation, we repeated all measurements 10 times).
   Especially the micro benchmark of the select-operator executes a lot of variants (even more than we show in the paper).
   Thus, it may take about 20 minutes.
   
   ```bash
   build/src/microbenchmarks/select_benchmark_2_t > select_benchmark.csv
   build/src/microbenchmarks/select_sum_benchmark > select_sum_benchmark.csv
   ```
   
4. **Analyze the Measurements**
   
   *Coming soon!*

## Reproducing the Star Schema Benchmark (SSB) Experiments

*Coming soon!*

##  Reproducing the Comparison of MorphStore and MonetDB

*Coming soon!*
