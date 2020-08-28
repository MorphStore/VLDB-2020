#!/bin/bash

#******************************************************************************
# Utility functions
#******************************************************************************

function print_headline1 () {
    printf "\n"
    printf "################################################################\n"
    printf "# $1\n"
    printf "################################################################\n"
    printf "\n"
}

function print_headline2 () {
    printf "\n"
    printf "================================================================\n"
    printf "= $1\n"
    printf "================================================================\n"
    printf "\n"
}

#******************************************************************************
# Functions for the individual steps
#******************************************************************************

function compile () {
    print_headline1 "Compilation Step"

    set -e

    cd $pathEngine

    local targets=""
    if [[ $useExample ]]
    then
        local targets="$targets otf_morphing_example_1"
    fi
    if [[ $useSingleOp ]]
    then
        local targets="$targets select_benchmark_2_t"
    fi
    if [[ $useSimpleQuery ]]
    then
        local targets="$targets select_sum_benchmark"
    fi

    ./build.sh -noSelfManaging -hi -j3 -mon ${psFlagMap[$processingStyle]} -bMbm --target "$targets" --tvl $pathTVL

    cd $pathRoot

    set +e

    print_headline1 "Done"
}

function run () {
    print_headline1 "Running Step"

    set -e

    mkdir --parents $pathArtifacts

    cd $pathEngine

    for i in $(seq $repetitions)
    do
        if [[ $useExample ]]
        then
            build/src/microbenchmarks/otf_morphing_example_1 > $pathArtifacts/example_$i.csv
        fi
        if [[ $useSingleOp ]]
        then
            build/src/microbenchmarks/select_benchmark_2_t > $pathArtifacts/singleop_$i.csv
        fi
        if [[ $useSimpleQuery ]]
        then
            build/src/microbenchmarks/select_sum_benchmark > $pathArtifacts/simplequery_$i.csv
        fi
    done

    cd $pathRoot

    set +e

    print_headline1 "Done"
}

function visualize () {
    print_headline1 "Visualization Step"

    set -e

    ### TODO Add this.

    set +e

    print_headline1 "Done"
}

# *****************************************************************************
# Some configuration
# *****************************************************************************

# -----------------------------------------------------------------------------
# Steps of this script's execution.
# -----------------------------------------------------------------------------

stepCompile=1
stepRun=2
stepVisualize=3
declare -A stepMap=(
    [c]=$stepCompile
    [compile]=$stepCompile
    [r]=$stepRun
    [run]=$stepRun
    [v]=$stepVisualize
    [visualize]=$stepVisualize
)

# -----------------------------------------------------------------------------
# Processing styles
# -----------------------------------------------------------------------------

psScalar="scalar<v64<uint64_t>>"
psSSE="sse<v128<uint64_t>>"
psAVX2="avx2<v256<uint64_t>>"
psAVX512="avx512<v512<uint64_t>>"
declare -A psFlagMap=(
    [$psScalar]=""
    [$psSSE]="-sse4"
    [$psAVX2]="-avxtwo"
    [$psAVX512]="-avx512"
)

# *****************************************************************************
# Argument parsing
# *****************************************************************************

# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

startStep=$stepCompile
endStep=$stepVisualize
processingStyle="avx512<v512<uint64_t>>"
repetitions=10
useExample="1"
useSingleOp="1"
useSimpleQuery="1"

# -----------------------------------------------------------------------------
# Parsing
# -----------------------------------------------------------------------------

while [[ $# -gt 0 ]]
do
    key="$1"
    case $key in
        -h|--help)
            # TODO Write help.
            print_help
            exit 0
            ;;
        -s|--start)
            if [[ ${stepMap[$2]+_} ]]
            then
                startStep=${stepMap[$2]}
                shift
            else
                printf "unknown step: $2\n"
                exit -1
            fi
            ;;
        -e|--end)
            if [[ ${stepMap[$2]+_} ]]
            then
                endStep=${stepMap[$2]}
                shift
            else
                printf "unknown step: $2\n"
                exit -1
            fi
            ;;
        -r|--rep|--repetitions)
            repetitions=$2
            shift
            ;;
        -ps|--processingStyle)
            processingStyle=$2
            shift
            ;;
        --onlyExample)
            useSingleOp=""
            useSimpleQuery=""
            ;;
        --onlySingleOp)
            useExample=""
            useSimpleQuery=""
            ;;
        --onlySimpleQuery)
            useExample=""
            useSingleOp=""
            ;;
        *)
            printf "unknown option: $key\n"
            exit -1
            ;;
    esac
    shift
done

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

if [[ $startStep -gt $endStep ]]
then
    printf "the start step must not come after the end step\n"
    exit -1
fi

# -----------------------------------------------------------------------------
# Setting some paths
# -----------------------------------------------------------------------------

pathRoot=$(pwd)

pathMorphStore=$pathRoot/MorphStore
pathEngine=$pathMorphStore/Engine
pathTVL=$pathMorphStore/TVLLib

pathArtifacts=$pathRoot/artifacts/microbenchmarks

# *****************************************************************************
# Execution of the selected steps
# *****************************************************************************

if [[ $startStep -le $stepCompile ]] && [[ $stepCompile -le $endStep ]]
then
    compile
fi

if [[ $startStep -le $stepRun ]] && [[ $stepRun -le $endStep ]]
then
    run
fi

if [[ $startStep -le $stepVisualize ]] && [[ $stepVisualize -le $endStep ]]
then
    visualize
fi