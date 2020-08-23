#!/bin/bash

set -e

# *****************************************************************************
# Defaults of arguments
# *****************************************************************************

scaleFactor=100
repetitions=10
processingStyle="avx512<v512<uint64_t>>"
queries="1.1 1.2 1.3 2.1 2.2 2.3 3.1 3.2 3.3 3.4 4.1 4.2 4.3"
findBest=""
findWorst=""
pathArtifacts="."
pathMal=""
pathRefRes=""

# *****************************************************************************
# Help message
# *****************************************************************************

function print_help () {
    echo "Usage: greedy.sh [-h] [-sf N] [-r N] [-ps PROCESSING_STYLE] [-q {N.N}]"
    echo "                 [--findBest] [--findWorst]"
    echo "                 [--pathArtifacts] [--pathMal] [--pathRefRes]"
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
    echo "  -ps PROCESSING_STYLE, --processingStyle PROCESSING_STYLE"
    echo "                         The processing style to use, e.g."
    echo "                         'scalar<v64<uint64_t>>' or 'avx512<v512<uint6_t>>'."
    echo "                         Defaults to '$processingStyle'."
    echo "  -q {N.N}, --query {N.N}, --queries {N.N}"
    echo "                         The numbers of the queries to execute. "
    echo "                         Multiple queries can be specified by "
    echo "                         passing a space-separated list enclosed "
    echo "                         in quotation marks. Defaults to all queries."
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
        -ps|--processingStyle)
            processingStyle=$2
            shift
            ;;
        -q|--query|--queries)
            queries=$2
            shift
            ;;
        --findBest)
            findBest=1
            ;;
        --findWorst)
            findWorst=1
            ;;
        --pathArtifacts)
            pathArtifacts=$2
            shift
            ;;
        --pathMal)
            pathMal=$2
            shift
            ;;
        --pathRefRes)
            pathRefRes=$2
            shift
            ;;
        *)
            printf "unknown option: $key\n"
            exit -1
            ;;
    esac
    shift
done

pathBest=$pathArtifacts/ssb_formats_bestperf_sf$scaleFactor
pathWorst=$pathArtifacts/ssb_formats_worstperf_sf$scaleFactor

# *****************************************************************************
# Creation of the results directories
# *****************************************************************************

if [[ $findBest ]]
then
    mkdir --parents $pathBest
fi
if [[ $findWorst ]]
then
    mkdir --parents $pathWorst
fi

# TODO Don't hardcode this path.
cd MorphStore/Benchmarks/ssb

# *****************************************************************************
# Execution of the greedy algorithm
# *****************************************************************************

# TODO The reference results should not be necessary here.
defaultArgs="-sf $scaleFactor -ps $processingStyle -r $repetitions --pathArtifacts $pathArtifacts --pathMal $pathMal --pathRefRes $pathRefRes"

for q in $queries
do
    if [[ $findBest ]]
    then
        ./greedy.py $defaultArgs -q $q -o $pathBest --findBest
    fi
    if [[ $findWorst ]]
    then
        ./greedy.py $defaultArgs -q $q -o $pathWorst --findWorst
    fi
done

set +e