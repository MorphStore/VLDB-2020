#!/bin/bash

set -e

# Some fixed configuration.
relPath="../../.."
actualBestDirName="ssb_formats_bestperf"
actualWorstDirName="ssb_formats_worstperf"

# Defaults of arguments.
scaleFactor=10
repetitions=5
findBest=""
findWorst=""

# *****************************************************************************
# Help message
# *****************************************************************************

function print_help () {
    echo "Usage: greedy.sh [-h] [-sf N] [-r N] [--findBest] [--findWorst]"
    echo ""
    echo "Determines the best and/or worst format combination w.r.t. "
    echo "performance for all SSB queries."
    echo ""
    echo "Prerequisites:"
    echo "  - You have set up the evaluation environment using "
    echo "    'setup_eval_env.sh'."
    echo ""
    echo "Optional arguments:"
    echo "  -h, --help             Show this help message and exit."
    echo "  -sf N, --scaleFactor N The SSB scale factor to use. Defaults to "
    echo "                         $scaleFactor."
    echo "  -r N, --repetitions N  The number of times to execute each "
    echo "                         query. Defaults to $repetitions."
    echo "  --findBest             Determine the best format combination for "
    echo "                         each query. Output is stored to directory "
    echo "                         '$actualBestDirName'."
    echo "  --findWorst            Determine the worst format combination for "
    echo "                         each query. Output is stored to directory "
    echo "                         '$actualWorstDirName'."
}

# *****************************************************************************
# Argument parsing
# *****************************************************************************

# Parse arguments.
while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -h|--help)
            print_help
            exit 0
            ;;
        -sf|--scaleFactor)
            scaleFactor=$2
            shift
            ;;
        -r|--repetitions)
            repetitions=$2
            shift
            ;;
        --findBest)
            findBest=1
            ;;
        --findWorst)
            findWorst=1
            ;;
        *)
            printf "unknown option: $key\n"
            exit -1
            ;;
    esac
    shift
done

# *****************************************************************************
# Creation of the results directories
# *****************************************************************************

if [[ $findBest ]]
then
    mkdir --parents $actualBestDirName
fi
if [[ $findWorst ]]
then
    mkdir --parents $actualWorstDirName
fi

cd MorphStore/Benchmarks/ssb

# *****************************************************************************
# Execution of the greedy algorithm
# *****************************************************************************

defaultArgs="-sf $scaleFactor -ps avx512<v512<uint64_t>> -r $repetitions"

for q in 1.1 1.2 1.3 2.1 2.2 2.3 3.1 3.2 3.3 3.4 4.1 4.2 4.3
do
    if [[ $findBest ]]
    then
        ./greedy.py $defaultArgs -q $q -o $relPath/$actualBestDirName --findBest
    fi
    if [[ $findWorst ]]
    then
        ./greedy.py $defaultArgs -q $q -o $relPath/$actualWorstDirName --findWorst
    fi
done

set +e