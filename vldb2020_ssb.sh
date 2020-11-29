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

function setup () {
    print_headline1 "Setup Step"

    set -e

    print_headline2 "Downloading and compiling the SSB data generator"
    
    # TODO Clone or submodule?
    git clone https://github.com/lemire/StarSchemaBenchmark.git
    mv StarSchemaBenchmark $pathDBGen
    cd $pathDBGen
    make -j8
    cd $pathRoot

    if [[ $useMonetDB ]]
    then
        print_headline2 "Downloading and compiling MonetDB"

        mkdir $pathMonetDB
        cd $pathMonetDB

        wget https://www.monetdb.org/downloads/sources/archive/MonetDB-11.31.13.tar.bz2
        tar -xvjf MonetDB-11.31.13.tar.bz2

        mkdir --parents $pathMonetDBInstalled
        cd MonetDB-11.31.13/
        ./configure --prefix=$pathMonetDBInstalled --enable-optimize
        make -j8
        make install

        cd $pathRoot

        printf "user=monetdb\npassword=monetdb" > $pathDotMonetDBFile

        eval $monetdbd create $pathMonetDBFarm
    fi

    set +e

    print_headline1 "Done"
}

function calibrate () {
    print_headline1 "Calibration Step"

    set -e

    mkdir --parents $pathProfiles

    cd $pathEngine

    ./build.sh -noSelfManaging -hi ${psFlagMap[$processingStyle]} -mon -bCa -j4

    # TODO These should be limited to only the selected processing style.
    build/src/calibration/bw_prof      $repetitions > $pathProfiles/bw_prof_alone.csv
    build/src/calibration/bw_prof_casc $repetitions > $pathProfiles/bw_prof_casc.csv
    build/src/calibration/const_prof   $repetitions > $pathProfiles/const_prof_casc.csv
    build/src/calibration/uncompr      $repetitions > $pathProfiles/uncompr.csv

    cd $pathRoot

    set +e

    print_headline1 "Done"
}

function generate () {
    print_headline1 "Generation Step"

    set -e

    print_headline2 "SSB data generation"
    cd $pathDBGen
    ./dbgen -f -s $scaleFactor -T a
    cd $pathRoot

    print_headline2 "SSB data dictionary coding"
    mkdir --parents $pathData
    # TODO Only create data for MorphStore if requested.
    eval $dbdict $schemaFullFile $schemaRequiredFile $pathDBGen $pathData

    print_headline2 "Deleting original .tbl-files"
    rm -f $pathDBGen/*.tbl

    if [[ $useMonetDB ]]
    then
        print_headline2 "Loading data into MonetDB"
        eval $monetdbd start $pathMonetDBFarm
        for intType in $intTypes
        do
            local dbName=${benchmark}_sf${scaleFactor}_${intType}
            set +e # continue if destruction fails
            eval $monetdb destroy -f $dbName
            set -e
            eval $monetdb create $dbName
            eval $monetdb release $dbName
            eval $createload $benchmark $schemaRequiredFile $pathDataTblsDict $intType $pathDataStatsDict \
                | $mclient -d $dbName
        done
        eval $monetdbd stop $pathMonetDBFarm
    fi

    print_headline2 "Deleting dictionary-encoded .tbl-files"
    rm -rf $pathDataTblsDict

    if [[ $useMorphStore ]]
    then
        # TODO The reference results should not be necessary.
        local generalFlags="-mem n -um s -sf $scaleFactor -s t --pathArtifacts $pathArtifacts --pathMal $pathMal --pathRefRes $pathRefRes"

        cd $pathBenchmarks/ssb

        print_headline2 "Analyzing data characteristics in MorphStore"
        ./ssb.sh $generalFlags -p d -q "$queries"
        
        print_headline2 "Determining compressed data sizes in MorphStore"
        ./ssb.sh $generalFlags -p s -q "$queries" -ps $processingStyle

        cd $pathRoot
        
        print_headline2 "Determining best/worst format combinations in MorphStore"
        # TODO The reference results should not be necessary here.
        ./greedy.sh -sf $scaleFactor -r $repetitionsGreedy -ps $processingStyle -q "$queries" --findBest --findWorst --pathArtifacts $pathArtifacts --pathMal $pathMal --pathRefRes $pathRefRes
    fi

    set +e

    print_headline1 "Done"
}

function run () {
    print_headline1 "Running Step"

    set -e

    if [[ $useMorphStore ]]
    then
        print_headline2 "SSB in MorphStore"

        mkdir --parents $pathTimesMorphStore

        cd $pathBenchmarks/ssb

        # ---------------------------------------------------------------------
        # Flags for calling MorphStore's SSB-script
        # ---------------------------------------------------------------------

        local generalFlags="-mem n -um s -sf $scaleFactor -p t"

        local keyUncomprScalar="UncomprScalar"
        local keyUncompr="Uncompr"
        local keyStaticBP32="StaticBP32"
        local keyActualBestPerf="ActualBestPerf"
        local keyActualBestBasePerf="ActualBestBasePerf"
        local keyActualWorstPerf="ActualWorstPerf"
        local keyCostBasedBestPerf="CostBasedBestPerf"

        local actualBestPerfFlags="-c manual -cconfig $pathBest"

        declare -A comprFlags=(
            [$keyUncomprScalar]="-c uncompr"
            [$keyUncompr]="-c uncompr"
            [$keyStaticBP32]="-c rulebased -crndu static_vbp_32"
            [$keyActualBestPerf]="$actualBestPerfFlags"
            [$keyActualBestBasePerf]="$actualBestPerfFlags -cuinterm yes"
            [$keyActualWorstPerf]="-c manual -cconfig $pathWorst"
            [$keyCostBasedBestPerf]="-c costbased -cobj perf -crndu static_vbp_bit -crnds static_vbp_bit"
        )

        local keys=""
        local keys="$keys $keyUncomprScalar"
        local keys="$keys $keyUncompr"
        local keys="$keys $keyStaticBP32"
        local keys="$keys $keyActualBestPerf"
        local keys="$keys $keyActualBestBasePerf"
        local keys="$keys $keyActualWorstPerf"
        local keys="$keys $keyCostBasedBestPerf"

        # ---------------------------------------------------------------------
        # Execution of the SSB in MorphStore
        # ---------------------------------------------------------------------

        for key in $keys
        do
            if [[ $key = $keyUncomprScalar ]]
            then
                processingStyleUse="scalar<v64<uint64_t>>"
            else
                processingStyleUse=$processingStyle
            fi
            local flags="$generalFlags ${comprFlags[$key]} -ps $processingStyleUse"

            printf "$key\n"

            printf "\tbuilding... "
            # TODO The reference results should ne be necessary here.
            ./ssb.sh $flags -s t -e b -q "$queries" --pathArtifacts $pathArtifacts --pathMal $pathMal --pathRefRes $pathRefRes > /dev/null 2> /dev/null
            printf "done.\n"

            printf "\trunning... "
            for i in $(seq $repetitions)
            do
                # TODO The reference results should ne be necessary here.
                ./ssb.sh $flags -s r -q "$queries" --pathArtifacts $pathArtifacts --pathRefRes $pathRefRes --pathTime $pathTimesMorphStore/${key}_$i > /dev/null 2> /dev/null
                printf "$i "
            done
            printf "done.\n"
        done

        cd $pathRoot
    fi
    
    if [[ $useMonetDB ]]
    then
        print_headline2 "SSB in MonetDB"

        mkdir --parents $pathTimesMonetDB

        cd $pathBenchmarks/ssb

        for intType in $intTypes
        do
            # We execute two extra repetitions, because we need to discard the
            # first two repetitions for a warm start.
            ./monetdb_ssb.sh -sf $scaleFactor -q "$queries" -r $((repetitions + 2)) -t $intType --pathMonetDB $pathMonetDBInstalled --pathMonetDBFarm $pathMonetDBFarm --pathMorphStore $pathMorphStore --pathData $pathData > $pathTimesMonetDB/${intType}.csv #2> /dev/null
        done

        cd $pathRoot
    fi

    set +e

    print_headline1 "Done"
}

function visualize () {
    print_headline1 "Visualization Step"

    set -e

    if [[ ! $useMorphStore ]]
    then
        local argWithoutMorphStore="--withoutMorphStore"
    fi
    if [[ ! $useMonetDB ]]
    then
        local argWithoutMonetDB="--withoutMonetDB"
    fi

    # Note: $queries must not be in quotation marks here.
    scripts/dias_ssb.py -sf $scaleFactor -ps $processingStyle -r $repetitions -q $queries $argWithoutMorphStore $argWithoutMonetDB

    set +e

    print_headline1 "Done"
}

# *****************************************************************************
# Some configuration
# *****************************************************************************

benchmark=ssb

# -----------------------------------------------------------------------------
# Steps of this script's execution.
# -----------------------------------------------------------------------------

stepSetup=1
stepCalibrate=2
stepGenerate=3
stepRun=4
stepVisualize=5
declare -A stepMap=(
    [s]=$stepSetup
    [setup]=$stepSetup
    [c]=$stepCalibrate
    [calibrate]=$stepCalibrate
    [g]=$stepGenerate
    [generate]=$stepGenerate
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

startStep=$stepSetup
endStep=$stepVisualize
scaleFactor=100
useMorphStore="1"
useMonetDB="1"
processingStyle="avx512<v512<uint64_t>>"
repetitions=10
repetitionsGreedy=3
queries="1.1 1.2 1.3 2.1 2.2 2.3 3.1 3.2 3.3 3.4 4.1 4.2 4.3"

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
        -sf|--scaleFactor)
            scaleFactor=$2
            shift
            ;;
        -q|--query|--queries)
            queries=$2
            shift
            ;;
        -r|--repetitions)
            repetitions=$2
            shift
            ;;
        -g|--repetitionsGreedy)
            repetitionsGreedy=$2
            shift
            ;;
        -ps|--processingStyle)
            processingStyle=$2
            shift
            ;;
        --withoutMorphStore)
            useMorphStore=""
            ;;
        --withoutMonetDB)
            useMonetDB=""
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
pathDBGen=$pathRoot/ssb-dbgen

pathMorphStore=$pathRoot/MorphStore
pathEngine=$pathMorphStore/Engine
pathBenchmarks=$pathMorphStore/Benchmarks

pathTools=$pathBenchmarks/tools
dbdict=$pathTools/dict/dbdict.py
createload=$pathTools/monetdb_create+load.py
schemaFullFile=$pathBenchmarks/ssb/schema_full.json
schemaRequiredFile=$pathBenchmarks/ssb/schema_required.json

pathArtifacts=$pathRoot/artifacts/ssb
pathProfiles=$pathArtifacts/compr_profiles
pathData=$pathArtifacts/data_sf$scaleFactor
pathDataTblsDict=$pathData/tbls_dict
pathDataStatsDict=$pathData/stats_dict
pathMal=$pathBenchmarks/ssb/mal_sf$scaleFactor
pathRefRes=$pathBenchmarks/ssb/refres_sf$scaleFactor
pathBest=$pathArtifacts/ssb_formats_bestperf_sf$scaleFactor
pathWorst=$pathArtifacts/ssb_formats_worstperf_sf$scaleFactor
pathTimesMorphStore=$pathArtifacts/times_MorphStore_sf${scaleFactor}
pathTimesMonetDB=$pathArtifacts/times_MonetDB_sf${scaleFactor}

pathMonetDB=$pathRoot/MonetDB
pathMonetDBInstalled=$pathMonetDB/monetdb
monetdbd=$pathMonetDBInstalled/bin/monetdbd
monetdb=$pathMonetDBInstalled/bin/monetdb
mclient=$pathMonetDBInstalled/bin/mclient
pathMonetDBFarm=$pathMonetDB/monetdbfarm
pathDotMonetDBFile=$pathMonetDB/.monetdb
intTypes="BIGINT tight"
if [[ $useMonetDB ]]
then
    export DOTMONETDBFILE=$pathDotMonetDBFile
fi

# *****************************************************************************
# Execution of the selected steps
# *****************************************************************************

# Stop the MonetDB daemon if it is still running.
eval $monetdbd stop $pathMonetDBFarm

if [[ $startStep -le $stepSetup ]] && [[ $stepSetup -le $endStep ]]
then
    setup
fi

if [[ $startStep -le $stepCalibrate ]] && [[ $stepCalibrate -le $endStep ]]
then
    calibrate
fi

if [[ $startStep -le $stepGenerate ]] && [[ $stepGenerate -le $endStep ]]
then
    generate
fi

if [[ $startStep -le $stepRun ]] && [[ $stepRun -le $endStep ]]
then
    run
fi

if [[ $startStep -le $stepVisualize ]] && [[ $stepVisualize -le $endStep ]]
then
    visualize
fi