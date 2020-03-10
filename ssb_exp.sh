#!/bin/bash

set -e

# Some fixed configuration.
scaleFactor=10
relPath="../../.."
resDirName="results_ssb"
actualBestDirName="ssb_formats_bestperf"
actualWorstDirName="ssb_formats_worstperf"

# Defaults of arguments.
repetitions=10
withActualBest=""
withActualWorst=""

# *****************************************************************************
# Help message
# *****************************************************************************

function print_help () {
    echo "Usage: ssb_exp.sh [-h] [-r N] [--withActualBest] [--withActualWorst]"
    echo ""
    echo "Executes the Star Schema Benchmark (SSB) experiments of Section 5.2 "
    echo "in our VLDB 2020 submission in MorphStore. All measurements files "
    echo "are placed in a directory named '$resDirName'."
    echo ""
    echo "Prerequisites:"
    echo "  - You have set up the evaluation environment using "
    echo "    'setup_eval_env.sh'."
    echo "  - To use the actual best or worst format combination w.r.t. "
    echo "    performance, you must have run the greedy algorithm to obtain "
    echo "    them. (Details on this will follow soon.)" #TODO
    echo ""
    echo "Optional arguments:"
    echo "  -h, --help             Show this help message and exit."
    echo "  -r N, --repetitions N  The number of times to execute each "
    echo "                         query. Defaults to $repetitions."
    echo "  --withActualBest       Use the format combinations in directory"
    echo "                         '$actualBestDirName' as the actual best "
    echo "                         format combination w.r.t. performance."
    echo "  --withActualWorst      Use the format combinations in directory"
    echo "                         '$actualWorstDirName' as the actual worst "
    echo "                         format combination w.r.t. performance."
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
        -r|--repetitions)
            repetitions=$2
            shift
            ;;
        --withActualBest)
            withActualBest=1
            ;;
        --withActualWorst)
            withActualWorst=1
            ;;
        *)
            printf "unknown option: $key\n"
            exit -1
            ;;
    esac
    shift
done

# *****************************************************************************
# Creation of the results directory
# *****************************************************************************

mkdir --parents $resDirName
cd MorphStore/Benchmarks/ssb

# *****************************************************************************
# Flags for calling MorphStore's SSB-script
# *****************************************************************************

defaultFlags="-mem n -um s -sf $scaleFactor -p t"

keyUncomprScalar="UncomprScalar"
keyUncompr="Uncompr"
keyStaticBP="StaticBP"
keyActualBestPerf="ActualBestPerf"
keyActualBestBasePerf="ActualBestBasePerf"
keyActualWorstPerf="ActualWorstPerf"

actualBestPerfFlags="-c manual -cconfig $relPath/$actualBestDirName"

declare -A comprFlags=(
    [$keyUncomprScalar]="-c uncompr"
    [$keyUncompr]="-c uncompr"
    [$keyStaticBP]="-c rulebased -crndu static_vbp_bit"
    [$keyActualBestPerf]="$actualBestPerfFlags"
    [$keyActualBestBasePerf]="$actualBestPerfFlags -cuinterm yes"
    [$keyActualWorstPerf]="-c manual -cconfig $relPath/$actualWorstDirName"
)

keys=""
keys="$keys $keyUncomprScalar"
keys="$keys $keyUncompr"
keys="$keys $keyStaticBP"
if [[ $withActualBest ]]
then
    keys="$keys $keyActualBestPerf"
    keys="$keys $keyActualBestBasePerf"
fi
if [[ $withActualWorst ]]
then
    keys="$keys $keyActualWorstPerf"
fi

# *****************************************************************************
# Execution of the SSB in MorphStore
# *****************************************************************************

printf "Executing the Star Schema Benchmark in MorphStore ($repetitions repetitions)\n"
for key in $keys
do
    if [[ $key = $keyUncomprScalar ]]
    then
        ps="scalar<v64<uint64_t>>"
    else
        ps="avx512<v512<uint64_t>>"
    fi
    flags="$defaultFlags ${comprFlags[$key]} -ps $ps"

    printf "\t$key\n"

    printf "\t\tbuilding... "
    ./ssb.sh $flags -s t -e b > /dev/null 2> /dev/null
    printf "done.\n"

    printf "\t\trunning... "
    for i in $(seq $repetitions)
    do
        ./ssb.sh $flags -s r > /dev/null 2> /dev/null
        mv time_sf$scaleFactor $relPath/$resDirName/time_sf${scaleFactor}_${key}_$i
        printf "$i "
    done
    printf "done.\n"
done


set +e