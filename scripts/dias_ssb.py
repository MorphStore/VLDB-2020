#!/usr/bin/env python3

"""
This script generates the diagrams for the Star Schema Benchmark experiments.

In particular, it generates Figures 1, 7, 8, 9, and 10 in the paper, using the
measurements obtained through the vldb2020_ssb.sh script.
"""

import argparse
import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import seaborn as sns

_pathMorphStore = "MorphStore"
sys.path.append(os.path.join(_pathMorphStore, "Benchmarks", "tools", "mal2x"))
sys.path.append(os.path.join(_pathMorphStore, "Benchmarks", "ssb"))
sys.path.append(os.path.join(_pathMorphStore, "LC-BaSe"))
import mal2morphstore.compr as compr
import mal2morphstore.formats as formats
import mal2morphstore.processingstyles as pss
import csvutils

import utils

# *****************************************************************************
# Utility functions
# *****************************************************************************
    
# -----------------------------------------------------------------------------
# Regarding memory footprints
# -----------------------------------------------------------------------------

def _getSizes(q, cs):
    """
    Retrieves the physical sizes (in bytes) of all columns (base, intermediate)
    of the given query using the specified strategy to determine the compressed
    formats.
    """
    
    def sizeStaticVBP(row):
        countValues = row[csvutils.ColInfoCols.countValues]
        bw = row["format"]._bw
        blockSize = pss.PS_INFOS[processingStyle].vectorSizeBit
        return int(
                # That many data elements...
                int(countValues / blockSize) * blockSize
                # ... are represented with bw bits each...
                * bw
                # ..., which is that many bytes.
                / 8
                # The remaining data elements are represented with 8 bytes each
                # (uncompressed 64-bit integers).
                + countValues % blockSize * 8
        )
    
    # Set the query-specific parameters for the cost-based format selection.
    if cs in ["ActualBestMem", "ActualBestBaseMem", "ActualWorstMem"]:
        querySpecificParams = dict(
                sizesFilePath=os.path.join(pathSizes, "q{}.csv".format(q))
        )
    elif cs in ["ActualBestPerf", "ActualBestBasePerf"]:
        querySpecificParams = dict(
                configFilePath=os.path.join(pathBest, "q{}.csv".format(q))
        )
    elif cs == "ActualWorstPerf":
        querySpecificParams = dict(
                configFilePath=os.path.join(pathWorst, "q{}.csv".format(q))
        )
    else:
        querySpecificParams = dict()

    # Load information on all columns involved in the query
    # (data characteristics, access characteristics).
    dfColInfos = csvutils.getColInfos(
            os.path.join(pathDataCh, "q{}.csv".format(q))
    )
    # Load the sizes of each column in each format, so that we can use the size
    # achieved with the selected format later on.
    # TODO There is a function for that in csvutils.
    dfSizes = csvutils.readMorphStoreCsv(
            os.path.join(pathSizes, "q{}.csv".format(q))
    )
    
    # Choose the compressed formats of all columns (base, intermediate)
    # involved in the specified query using the specified compression strategy.
    df = compr.choose(
        dfColInfos, processingStyle,
        objective="perf" if "Perf" in cs else "mem",
        **querySpecificParams, **chooseParams[cs],
    ).reset_index()
    df.columns = ["colName", "format"]
    df["formatWithBw"] = df["format"].apply(lambda fmt: fmt.getInternalName())
    df["query"] = q
    df["cs"] = cs

    # Fetch the column information (data and access characteristics) of each
    # column involved in the query.
    df = df.merge(
            dfColInfos.reset_index()[
                    ["colName", csvutils.ColInfoCols.countValues]
            ],
            on=["colName"]
    )
    
    sIsStaticVBP = df["format"].apply(
            lambda fmt: isinstance(fmt, formats.StaticVBPFormat)
    )
    # Calculate the memory footprint of each column for which the format
    # static_vbp was chosen using the chosen bit width. Note two things:
    # - This footprint can be calculated accurately without knowing the actual
    #   data. Only the number of data elements and the bit width are decisive.
    # - Since this can easily be calculated, we do not measure it when we
    #   determine the size of each column in each format.
    dfStatic = df[sIsStaticVBP].copy()
    if len(dfStatic):
        dfStatic["sizeUsedByte"] = dfStatic.apply(sizeStaticVBP, axis=1)
    else:
        dfStatic["sizeUsedByte"] = 0 # only to add the column to the data frame
    # Fetch the memory footprint of each column for which another format than
    # static_vbp was chosen, using the format chosen for the particular column.
    dfOther = df[~sIsStaticVBP]
    dfOther = dfOther.merge(
            dfSizes[["colName", "formatWithBw", "sizeUsedByte"]],
            on=["colName", "formatWithBw"]
    )
    # Combine everything.
    df = dfStatic.append(dfOther)
    
    return df

# -----------------------------------------------------------------------------
# Loading measurements
# -----------------------------------------------------------------------------

def loadFootprintsMorphStore():
    """Loads the memory footprints in MorphStore."""
    
    # Utility function.
    def enrichDf(df, q, ps, cs):
        df["query"] = q
        df["ps"] = ps
        df["cs"] = cs
        return df
    
    # Retrieve the memory footprints of the individual columns according to the
    # format combination implied by the respective compression strategy.
    dfs = []
    for q in queries:
        for cs in [cs.format(obj="Mem") for cs in comprStrategiesFss]:
            dfs.append(enrichDf(_getSizes(q, cs), q, processingStyle, cs))
    dfMem = pd.concat(dfs)

    # Drop some unnecessary attributes.
    dfMem.drop(
            columns=["colName", "format", "formatWithBw", "countValues:"],
            inplace=True
    )
    # Calculate the total memory footprint for each query by adding up the
    # footprints of all involved columns.
    dfMem = dfMem.groupby(["query", "cs", "ps"], as_index=False).sum()

    # Calculate the average memory footprint over all queries.
    dfMemAvg = dfMem.groupby(["cs", "ps"], as_index=False).mean()
    dfMemAvg["query"] = "avg"
    dfMem = dfMem.append(
            dfMemAvg[["query", "cs", "ps", "sizeUsedByte"]]
    )

    # Calculate the memory footprint in GiB.
    dfMem["footprint [GiB]"] = dfMem["sizeUsedByte"] / 1024 / 1024 / 1024
    
    return dfMem

def loadRuntimesMorphStore():
    """Loads the measured MorphStore runtimes."""
    
    # Utility function.
    def enrichDf(df, q, ps, cs):
        # TODO So actually, we need to load/parse only the fifth line of each
        # file... Could be faster...
        # Consider only the runtime of the entire query (not those of the
        # individual operators).
        df = df[df["opIdx"] == 0].copy()
        # Drop unnecessary columns.
        df.drop(columns=["opIdx", "opName"], inplace=True)
        # Add some attributes given by the context.
        df["query"] = q
        df["ps"] = ps
        df["cs"] = cs
        return df
    
    # Load the measured runtimes.
    dfs = []
    csUncomprScalar = "UncomprScalar"
    for repIdx in range(1, countReps + 1):
        for q in queries:
            for cs in [cs.format(obj="Perf") for cs in comprStrategiesFss + [csUncomprScalar]]:
                dfs.append(enrichDf(
                        csvutils.readMorphStoreCsv(os.path.join(
                                pathTimesMorphStore,
                                "time_sf{}_{}_{}".format(scaleFactor, cs, repIdx),
                                "q{}.csv".format(q)
                        )),
                        q,
                        psNames[
                                # For the uncompressed compression strategy, we
                                # also used the scalar processing style.
                                pss.PS_SCALAR
                                if cs == csUncomprScalar
                                else processingStyle
                        ],
                        cs
                ))
    dfPerf = pd.concat(dfs)

    # Calculate the average runtime over all queries.
    dfPerfAvg = dfPerf.groupby(["ps", "cs"], as_index=False).mean()
    dfPerfAvg["query"] = "avg"
    dfPerf = dfPerf.append(
            dfPerfAvg[["runtime", "query", "ps", "cs"]]
    )

    # Calculate the runtime in seconds.
    dfPerf["runtime [s]"] = dfPerf["runtime"] / 1000 / 1000
    
    return dfPerf

def loadRuntimesMonetDB(intType):
    """Loads the measured MonetDB runtimes."""
    
    # Load the measured runtimes.
    dfPerf = pd.read_csv(
            os.path.join(pathTimesMonetDB, "{}.csv".format(intType)), sep="\t"
    )
    
    # Drop the first two repetitions, since they are usually slow.
    dfPerf = dfPerf[dfPerf["repetition"] > 2]
    dfPerf.drop(columns="repetition", inplace=True)

    # Some post-processing.
    dfPerf["query"] = dfPerf["query"].astype(str)
    dfPerf["ps"] = psNames[pss.PS_SCALAR]
    dfPerf["cs"] = intType
    dfPerf["runtime [s]"] = dfPerf["runtime [ms]"] / 1000
    dfPerf = dfPerf[["query", "ps", "cs", "runtime [s]"]]
    
    # Consider only the specified queries.
    dfPerf = dfPerf[dfPerf["query"].isin(queries)]

    # Calculate the average runtime over all queries.
    dfPerfAvg = dfPerf.groupby(["ps", "cs"], as_index=False).mean()
    dfPerfAvg["query"] = "avg"
    dfPerf = dfPerf.append(
            dfPerfAvg[["query", "ps", "cs", "runtime [s]"]]
    )

    return dfPerf

# -----------------------------------------------------------------------------
# Regarding diagrams
# -----------------------------------------------------------------------------

def _drawDia(hueCol, hueOrder, palette, dfMem, dfPerf, rowH=3):
    """Draws a typical diagram."""
    
    diaIdx = 0
    rowInfo = []
    if dfMem is not None:
        rowInfo.append(
                ("Mem", dfMem, "footprint [GiB]", "total memory footprint [GiB]")
        )
    if dfPerf is not None:
        rowInfo.append(
                ("Perf", dfPerf, "runtime [s]", "total runtime [s]")
        )
    countRows = len(rowInfo)
    fig = plt.figure(figsize=(10, rowH * countRows))
    for obj, df, yCol, title in rowInfo:
        diaIdx += 1
        ax = fig.add_subplot(countRows, 1, diaIdx)
        sns.barplot(
            ax=ax,
            y=yCol, x="query", ci=None,
            hue=hueCol, hue_order=[val.format(obj) for val in hueOrder],
            palette=palette,
            data=df, edgecolor="black", lw=1, saturation=1,
        )
        ax.set_ylabel(None)
        ax.set_xlabel("SSB query")
        ax.set_title("({}) {} @sf {}".format(
                chr(ord("a") + diaIdx - 1), title, scaleFactor)
        )
        ax.get_legend().remove()
    sns.despine()
    fig.tight_layout()

# -----------------------------------------------------------------------------
# Generation of the individual diagrams in the paper.
# -----------------------------------------------------------------------------
    
def drawFigure1():
    """Draws Figure 1 (teaser diagram in the introduction)."""
    
    fig = plt.figure(figsize=(9, 4))
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    sns.barplot(
        ax=ax1,
        x="footprint [GiB]", y="cs",
        order=["Uncompr", "ActualBestBaseMem", "ActualBestMem"],
        data=dfMemMorphStore.query("query == 'avg'")
    )
    sns.barplot(
        ax=ax2,
        x="runtime [s]", y="cs",
        order=["Uncompr", "ActualBestBasePerf", "ActualBestPerf"],
        data=dfPerfMorphStore.query("query == 'avg'")
    )
    for ax in [ax1, ax2]:
        ax.set_yticklabels([
            "No\ncompression\nat all",
            "Established\nbase data\ncompression",
            "Our novel\ncontinuous\ncompression"
        ])
        ax.set_ylabel(None)
    ax2.set_yticks([])
    fig.tight_layout()
    sns.despine()
    utils.saveFig("figure01_teaser")

def drawFigure7():
    """Draws Figure 7 (impact of the format combination)."""
    
    colors = [colorRed, colorGray, colorBlue, colorGreen]
    order = ["ActualWorst{}", "Uncompr", "StaticBP32", "ActualBest{}"]
    labels = ["worst combination", "uncompressed", "Static-BP-32", "best combination"]

    filename = "figure07_ssb_formats"

    _drawDia("cs", order, colors, dfMemMorphStore, dfPerfMorphStore)
    utils.saveFig(filename)

    utils.drawLegendRect(labels, colors)
    utils.saveFig(filename + "_legend")

def drawFigure8():
    """Draws Figure 8 (compression of base data vs. intermediates)."""
    
    colors = [colorGray, colorCyan, colorYellow]
    order = ["Uncompr", "ActualBestBase{}", "ActualBest{}"]
    labels = ["uncompressed", "+ compressed base columns", "+ compressed intermediates"]

    filename = "figure08_ssb_base_vs_interm"

    _drawDia("cs", order, colors, dfMemMorphStore, dfPerfMorphStore)
    utils.saveFig(filename)

    utils.drawLegendRect(labels, colors)
    utils.saveFig(filename + "_legend")

def drawFigure10():
    """Draws Figure 10 (fitness of our cost-based format selection)."""
    
    colors = [colorRed, colorGray, colorYellow, colorGreen]
    order = ["ActualWorst{}", "Uncompr", "CostBasedBest{}", "ActualBest{}"]
    labels = ["worst combination", "uncompressed", "cost-based", "best combination"]

    filename = "figure10_opt"

    _drawDia("cs", order, colors, dfMemMorphStore, dfPerfMorphStore)
    utils.saveFig(filename)

    utils.drawLegendRect(labels, colors)
    utils.saveFig(filename + "_legend")

def drawFigure9():
    """Draws Figure 9 (comparision of MorphStore and MonetDB)."""
    
    dfs = []
    
    if useMorphStore:
        df = dfPerfMorphStore.query(
                "(cs in ['ActualBestPerf', 'Uncompr', 'UncomprScalar', 'ActualBestBasePerf'])".format(scaleFactor)
        )[["query", "ps", "cs", "runtime [s]"]].copy()
        df["candidate"] = df.apply(
                lambda row: "MorphStore {} {}".format(row["ps"], row["cs"]),
                axis=1
        )
        dfs.append(df)
    if useMonetDB:
        for intType in intTypesMonetDB:
            df = dfPerfMonetDB[intType]
            df["candidate"] = "MonetDB scalar {}".format(intType)
            dfs.append(df)
        
    dfComp = pd.concat(dfs)
    
    if useMorphStore:
        colors = [colorYellow, colorOrange, colorRed]
        order = [
            "MorphStore scalar UncomprScalar",
            "MorphStore {} Uncompr".format(psNames[processingStyle]),
            "MorphStore {} ActualBestPerf".format(psNames[processingStyle]),
        ]
        labels = [
            "MorphStore\nscalar\nuncompr.",
            "MorphStore\n{}\nuncompr.".format(psNames[processingStyle]),
            "MorphStore\n{}\ncontinuous compr.".format(psNames[processingStyle]),
        ]
    else:
        colors = []
        order = []
        labels = []
    if useMonetDB:
        colors = [colorCyan, *colors, colorBlue]
        order = [
            "MonetDB scalar BIGINT",
            *order,
            "MonetDB scalar tight",
        ]
        labels = [
            "MonetDB\nscalar\nuncompr.",
            *labels,
            "MonetDB\nscalar\nnarrow types",
        ]

    filename = "figure09_morphstore_vs_monetdb"

    _drawDia("candidate", order, colors, None, dfComp, 3.09)
    ax = plt.gca()
    ax.set_title(ax.get_title()[4:]) # remove the letter "(a)" in the title
    utils.saveFig(filename)

    utils.drawLegendRect(labels, colors)
    utils.saveFig(filename + "_legend")
    

# *****************************************************************************
# Main program
# *****************************************************************************

if __name__ == "__main__":
    # -------------------------------------------------------------------------
    # Argument parsing
    # -------------------------------------------------------------------------
    
    # Defaults.
    scaleFactor = 100
    processingStyle = pss.PS_VEC512
    queries = list(sorted(["{}.{}".format(mj, mn) for mj in range(1, 4+1) for mn in range(1, 3+1)] + ["3.4"]))
    countReps = 10
    
    # Set up the parser.
    # TODO Provide help messages.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
            "-sf", "--scaleFactor", metavar="N", type=int,
            help="",
            default=scaleFactor
    )
    parser.add_argument(
            "-ps", "--processingStyle", metavar="PROCESSING_STYLE",
            help="",
            default=processingStyle
    )
    parser.add_argument(
            "-r", "--repetitions", metavar="N", type=int,
            help="",
            default=countReps
    )
    parser.add_argument(
            "-q", "--query", "--queries", metavar="N.N", nargs="+",
            help="",
            default=queries, choices=queries,
    )
    parser.add_argument(
            "--withoutMorphStore", dest="useMorphStore", action="store_false",
            help="",
            default=True,
    )
    parser.add_argument(
            "--withoutMonetDB", dest="useMonetDB", action="store_false",
            help="",
            default=True,
    )
    
    # Parse arguments.
    args = parser.parse_args()
    scaleFactor = args.scaleFactor
    processingStyle = args.processingStyle
    queries = args.query
    countReps = args.repetitions
    useMorphStore = args.useMorphStore
    useMonetDB = args.useMonetDB
    
    # Validate arguments.
    # TODO

    # -------------------------------------------------------------------------
    # Setting the paths to certain artifacts
    # -------------------------------------------------------------------------

    pathArtifacts = os.path.join("artifacts", "ssb")
    pathProfiles = os.path.join(pathArtifacts, "compr_profiles")
    pathTimesMorphStore = os.path.join(pathArtifacts, "times_MorphStore_sf{}".format(scaleFactor))
    pathTimesMonetDB = os.path.join(pathArtifacts, "times_MonetDB_sf{}".format(scaleFactor))
    pathDataCh = os.path.join(pathArtifacts, "dc_sf{}".format(scaleFactor))
    pathSizes = os.path.join(pathArtifacts, "size_sf{}_{}".format(scaleFactor, processingStyle))
    pathDias = os.path.join(pathArtifacts, "dias_sf{}".format(scaleFactor))
    pathBest = os.path.join(pathArtifacts, "ssb_formats_bestperf_sf{}".format(scaleFactor))
    pathWorst = os.path.join(pathArtifacts, "ssb_formats_worstperf_sf{}".format(scaleFactor))
    
    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------
    
    # Compression strategies for loading the data. (Format strings, objective
    # is inserted when loading the data).
    comprStrategiesFss = [
        "Uncompr",
        "StaticBP32",
        "ActualWorst{obj}",
        "ActualBest{obj}",
        "ActualBestBase{obj}",
        "CostBasedBest{obj}",
    ]
    
    # For the cost-based format selection: Here we set the parameters to use
    # for each compression strategy. However, there are also some
    # query-specific parameters which are set elsewhere.
    staticVbpBit = formats.byName("static_vbp_bit", processingStyle)
    staticVbpPot = formats.byName("static_vbp_pot", processingStyle)
    staticVbp32 = formats.byName("static_vbp_32", processingStyle)
    uncompr = formats.UncomprFormat()
    rndBestMem=dict(fnRndAccUnsorted=staticVbpBit, fnRndAccSorted=staticVbpBit)
    rndBestPerf=dict(fnRndAccUnsorted=staticVbpBit, fnRndAccSorted=staticVbpBit)
    rndWorst=dict(fnRndAccUnsorted=uncompr, fnRndAccSorted=uncompr)
    chooseParams = {
        "Uncompr": dict(strategy="uncompr"),
        "StaticBP32": dict(strategy="rulebased", fnRndAccUnsorted=staticVbp32, fnRndAccSorted=staticVbp32, fnSeqAccUnsorted=staticVbp32, fnSeqAccSorted=staticVbp32),
        "ActualWorstMem": dict(strategy="realworst", **rndWorst),
        "ActualWorstPerf": dict(strategy="manual"),
        "ActualBestMem": dict(strategy="realbest", **rndBestMem),
        "ActualBestPerf": dict(strategy="manual"),
        "ActualBestBaseMem": dict(strategy="realbest", uncomprInterm=True, **rndBestMem),
        "ActualBestBasePerf": dict(strategy="manual", uncomprInterm=True),
        "CostBasedBestMem": dict(strategy="costbased", profileDirPath=pathProfiles, **rndBestMem),
        "CostBasedBestPerf": dict(strategy="costbased", profileDirPath=pathProfiles, **rndBestPerf),
    }
    
    # Human-readable names of the processing styles.
    psNames = {
        pss.PS_SCALAR: "scalar",
        pss.PS_VEC128: "SSE",
        pss.PS_VEC256: "AVX2",
        pss.PS_VEC512: "AVX-512",
    }
    
    # Integer types we used for the base data in MonetDB.
    intTypesMonetDB = ["BIGINT", "tight"]
    
    # -------------------------------------------------------------------------
    # Load the measurements
    # -------------------------------------------------------------------------
    
    print("Loading measurements... ", end="")
    sys.stdout.flush()
    
    if useMorphStore:
        dfMemMorphStore = loadFootprintsMorphStore()
        dfPerfMorphStore = loadRuntimesMorphStore()
    if useMonetDB:
        dfPerfMonetDB = {
            intType: loadRuntimesMonetDB(intType)
            for intType in intTypesMonetDB
        }
        
    print("done.")
    
    # -------------------------------------------------------------------------
    # Diagram generation
    # -------------------------------------------------------------------------
    
    print("Generating diagrams... ", end="")
    sys.stdout.flush()
    
    os.makedirs(pathDias, exist_ok=True)
    
    colorRed = "#f47264"
    colorGray = "#bfbfbf"
    colorBlue = "#868ad1"
    colorGreen = "#84cbc5"
    colorCyan = "#7cc8ec"
    colorYellow = "#f8d35e"
    colorOrange = "#ffa300"
    
    utils.pathDias = pathDias
    
    if useMorphStore:
        sns.set_context("talk", 1.0)
        utils.setMatplotlibRcParamsLikeInJupyterNotebook()
        drawFigure1()
        
        sns.set_context("talk", 1.1)
        utils.setMatplotlibRcParamsLikeInJupyterNotebook()
        drawFigure7()
        drawFigure8()
        drawFigure10()
        
    if useMorphStore or useMonetDB:
        sns.set_context("talk", 1.1)
        utils.setMatplotlibRcParamsLikeInJupyterNotebook()
        drawFigure9()
    
    print("done.")