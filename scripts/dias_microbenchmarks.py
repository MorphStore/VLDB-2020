#!/usr/bin/env python3

"""
This script generates the diagrams for micro benchmark experiments.

In particular, it generates Figures 4, 5, and 6 in the paper, using the
measurements obtained through the vldb2020_microbenchmarks.sh script.
"""

import argparse
import os
import sys

import matplotlib as mpl
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

_pathMorphStore = "MorphStore"
sys.path.append(os.path.join(_pathMorphStore, "Benchmarks", "tools", "mal2x"))
import mal2morphstore.processingstyles as pss

import utils

# *****************************************************************************
# Utility functions
# *****************************************************************************

# -----------------------------------------------------------------------------
# Loading measurements
# -----------------------------------------------------------------------------

def loadMeaFigure4():
    """Loads the measurements for Figure 4 (experiment on operator classes)."""
    
    # Utility function.
    def getInputSize(inDataFmt):
        countValues = 512 * 1024 * 1024
        if inDataFmt == "uncompr_f":
            bytes = countValues * 8
        elif inDataFmt.startswith("static_vbp_f<vbp_l<4, "):
            bytes =  countValues * 4 / 8
        elif inDataFmt.startswith("static_vbp_f<vbp_l<3, "):
            bytes =  countValues * 3 / 8
        else:
            raise RuntimeError()
        return bytes / 1024 ** 3
    
    # Load the measurements from the individual repetitions.
    dfs = []
    for repIdx in range(1, countReps + 1):
        df = pd.read_csv(
                os.path.join(pathArtifacts, "example_{}.csv".format(repIdx)),
                sep="\t",
                skiprows=2
        ).query("vector_extension != 'ps_scalar'")
        dfs.append(df)
    
    # Combine the repetitions.
    dfMea = pd.concat(dfs)
    
    # Derive some attributes and convert units.
    dfMea["operator_class_long"] = \
        dfMea.apply(lambda row: variantMap[row["operator_class"]], axis=1)
    dfMea["runtime [ms]"] = dfMea["runtime:µs"] / 1000
    dfMea["input size [MiB]"] = dfMea["in_data_f"].apply(getInputSize) * 1024
    
    return dfMea

def loadMeaFigure5():
    """
    Loads the measurements for Figure 5 (experiment on a single on-the-fly
    de/re-compression operator).
    """
    
    # Load the measurements of the individual repetitions.
    dfs = []
    for repIdx in range(1, countReps + 1):
        df = pd.read_csv(
                os.path.join(pathArtifacts, "singleop_{}.csv".format(repIdx)),
                sep="\t",
                skiprows=2
        )
        df.drop(columns=["pred", "check", "runtime:µs"])
        df["sel"] = df["datasetIdx"].apply(
                lambda datasetIdx: 0.01 if datasetIdx <= 6 else 0.9
        )
        df["col"] = (df["datasetIdx"] - 1).mod(6).map({
            0: "C1",
            1: "C2",
            2: "C3",
            3: "(not used)",
            4: "C4",
            5: "C5",
        })
        df = df.query("col != '(not used)'").copy()
        dfs.append(df)
    
    # Combine the repetitions and calculate the mean.
    dfMea = pd.concat(dfs).groupby(
            ["vector_extension", "out_pos_f", "in_data_f", "datasetIdx", "sel", "col"],
            as_index=False
    ).mean()
    
    # Derive some attributes and convert units.
    dfMea["runtime [ms]"] = dfMea["runtime select:µs"] / 1000
    def classify(row):
        outPosF = row["out_pos_f"]
        inDataF = row["in_data_f"]
        if outPosF == "uncompr_f" and inDataF == "uncompr_f":
            return "alluncompr"
        elif outPosF == "uncompr_f" and inDataF != "uncompr_f":
            return "outuncompr"
        else:
            return "outcompr"
    dfMea["class"] = dfMea.apply(classify, axis=1)
    
    return dfMea

def loadMeaFigure6():
    """Loads the measurements for Figure 6 (experiment on a simple query)."""
    
    # Load the measurements of the individual repetitions.
    dfs = []
    for repIdx in range(1, countReps + 1):
        # Load the data.
        df = pd.read_csv(
            os.path.join(pathArtifacts, "simplequery_{}.csv".format(repIdx)),
            sep="\t",
            skiprows=2
        )
        # Discard the warm-up measurement.
        df = df.query("settingIdx > 1").copy()
        # Derive some attributes for later.
        df["case"] = df["settingIdx"].map({
            2: "case 1\nX=C1\nY=C1",
            3: "case 2\nX=C1\nY=C4",
            4: "case 3\nX=C2\nY=C3",
        })
        df["fmts"] = df.apply(
            lambda row: "{} {} {} {}".format(
                    row["in_data_x_f"][0:2],
                    row["in_data_y_f"][0:2],
                    row["mid_pos_xc_f"][0:2],
                    row["mid_data_yc_f"][0:2]
            ),
            axis=1
        )
        dfs.append(df)
    
    # Combine the repetitions and calculate the mean.
    dfMea = pd.concat(dfs).groupby(
            [
                "vector_extension",
                "in_data_x_f", "in_data_y_f", "mid_pos_xc_f", "mid_data_yc_f",
                "settingIdx", "case", "fmts"
            ],
            as_index=False
    ).mean()

    # Convert units of runtimes and sizes.
    for colName in ["inDataX", "inDataY", "midPosXC", "midDataYC"]:
        dfMea["{} [GiB]".format(colName)] = \
                dfMea["{}_sizeUsedByte".format(colName)] / 1024 / 1024 / 1024
    for opName in ["select", "project", "agg_sum"]:
        dfMea["{} [s]".format(opName)] = \
                dfMea["runtime {}:µs".format(opName)] / 1000 / 1000
        
    return dfMea

# -----------------------------------------------------------------------------
# Generation of the individual diagrams in the paper.
# -----------------------------------------------------------------------------

def drawFigure4(dfMea, selectivity):
    """Draws Figure 4 (experiment on operator classes)"""
    
    fig = plt.figure(figsize=(7.5, 3.5))
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    
    dfUse = dfMea.query("sel == {}".format(selectivity))
    
    rtUncompr = dfUse.query("operator_class == 'uncompressed'")["runtime [ms]"].mean()
    rtOtfDrc = dfUse.query("operator_class == 'otf de/re-compression'")["runtime [ms]"].mean()
    rtSpecOp = dfUse.query("operator_class == 'specialized'")["runtime [ms]"].mean()
    rtOtfMor = dfUse.query("operator_class == 'otf morphing'")["runtime [ms]"].mean()
    
    # Number for the text
    if False:
        print("speedup OtfDrc vs. Uncompr: {}".format(rtUncompr / rtOtfDrc))
        print("speedup SpecOp vs. OtfDrc: {}".format(rtOtfDrc / rtSpecOp))
        print("slowdown OtfMor vs. SpecOp: {}".format(rtOtfMor / rtSpecOp))
    
    sns.barplot(
        ax=ax1,
        x="runtime [ms]", y="operator_class_long",
        order=[VAR_UU, VAR_OTFDRC, VAR_SPEC, VAR_OTFM],
        data=dfUse, ci=None,
    )
    ax1.set_ylabel(None);
    runtimeCap = 75
    ax1.set_xlim(right=runtimeCap);
    ax1.text(
        runtimeCap, 0, "{:.0f} ms → ".format(rtUncompr),
        horizontalalignment="right", verticalalignment="center", color="white",
        fontsize=20
    )
    
    sns.barplot(
        ax=ax2,
        x="input size [MiB]",
        y="operator_class_long",
        order=[VAR_UU, VAR_OTFDRC, VAR_SPEC, VAR_OTFM],
        data=dfUse,
        ci=None,
    )
    ax2.set_ylabel(None)
    ax2.set_yticklabels([])
    footprintCap = 512
    ax2.set_xlim(right=footprintCap)
    ax2.set_xticks([0, 128, 256, 384, 512])
    ax2.text(
        footprintCap,
        0,
        "{:.0f} MiB → ".format(
                dfUse.query("in_data_f == 'uncompr_f'")["input size [MiB]"].mean()
        ),
        horizontalalignment="right",
        verticalalignment="center",
        color="white",
        fontsize=20
    )
    
    sns.despine()
    utils.saveFig("figure4_example")

def _drawStackedBars(
        dfMea, cols, suffix, yLabel, shortTitle, shortMap, letter, ax, colors
):
    """Utility function for drawing a stacked bar plot."""
    
    hatches = [3*"/", " ", 3*".", 3*"\\"][:len(cols)]
    
    # Calculate the cumulative sum over the columns to display to achieve
    # stacked bars.
    colNamesOld = ""
    sumColNames = []
    for colIdx, colName in enumerate(cols):
        colNamesNew = "{}{}".format(colNamesOld, colName)
        if colNamesOld != "":
            dfMea["{}{}".format(colNamesNew, suffix)] = \
                dfMea["{}{}".format(colNamesOld, suffix)] + \
                dfMea["{}{}".format(colName, suffix)]
        sumColNames.append(colNamesNew)
        colNamesOld = colNamesNew
        
    # Draw an individual bar plot for each column to display to achieve stacked
    # bars.
    for colName, hatch in reversed(list(zip(sumColNames, hatches))):
        sns.barplot(
            ax=ax, data=dfMea,
            y="{}{}".format(colName, suffix),
            x="case",
            order=sorted(list(dfMea["case"].unique())),
            hue="fmts",
            hue_order=[
                "un un un un",
                "st st un un",
                "st st st st",
                "st st de de",
                "st st fo fo"
            ],
            palette=colors,
            edgecolor="black",
            hatch=hatch,
            saturation=1,
        )
        
    # Remove the auto-generated legend and create a custom one.
    ax.get_legend().remove()
    ax.legend(
        handles=[
            patches.Rectangle(
                    (0, 0), 1, 1,
                    facecolor="white", edgecolor="black", hatch=hatch
            )
            for hatch in reversed(hatches)
        ],
        labels=[shortMap[colName] for colName in reversed(cols)],
        title=shortTitle,
        title_fontsize=16,
        bbox_to_anchor=(1, 0.5),
        loc="center left",
        handlelength=1,
        handletextpad=0.5,
    )
    
    # And some post-processing.
    ax.set_ylabel(None)
    ax.set_title("({}) {}{}".format(letter, yLabel, suffix))
    ax.set_xlabel(None)
    sns.despine()
    
def drawFigure5(dfMea):
    """
    Draws Figure 5 (experiment on a single on-the-fly de/re-compression
    operator)
    """
    
    # Create the main figure.
    fig = plt.figure(figsize=(10, 4))
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    
    # Plot the data.
    for diaIdx, (ax, sel) in enumerate([
        (ax1, 0.01),
        (ax2, 0.9),
    ]):
        sns.swarmplot(
            ax=ax,
            y="runtime [ms]", x="col",
            hue="class", hue_order=["alluncompr", "outuncompr", "outcompr"],
            palette=["red", "blue", "silver"],
            data=dfMea.query("sel == {}".format(sel))
        )
        ax.set_title("({}) {:.0%} selectivity".format(chr(ord("a") + diaIdx), sel))
        ax.set_xlabel("input column")
        ax.set_ylim(bottom=0)
        ax.get_legend().remove()
    
    # Some post-processing.
    ax2.set_ylabel(None)
    sns.despine()
    fig.tight_layout()
    
    filename = "figure5_singleop"
    
    # Save the main figure.
    utils.saveFig(filename)
    
    utils.drawLegendMarker(
            [
                "uncompressed",
                "only input compressed",
                "input and output compressed"
            ],
            ["red", "blue", "silver"]
    )
    utils.saveFig(filename + "_legend")
    
    
def drawFigure6(dfMea):
    """Draws Figure 6 (experiment on a simple query)"""
    
    colors = ["#bfbfbf", "#7cc8ec", "#868ad1", "#f8d35e", "#f47264"]
    
    # Create the main figure.
    fig = plt.figure(figsize=(10, 4))
    ax1 = fig.add_subplot(121)
    ax2 = fig.add_subplot(122)
    
    filename = "figure6_simplequery"
    
    # For the memory footprints.
    _drawStackedBars(
            dfMea,
            ["inDataX", "inDataY", "midPosXC", "midDataYC"],
            " [GiB]",
            "memory footprint",
            "column",
            {
                "inDataX": "X",
                "inDataY": "Y",
                "midPosXC": "X'",
                "midDataYC": "Y'",
            },
            "a",
            ax1,
            colors
    )
    # For the runtimes.
    _drawStackedBars(
            dfMea,
            ["select", "project", "agg_sum"],
            " [s]",
            "runtime",
            "operator",
            {
                "select": "select",
                "project": "project",
                "agg_sum": "sum",
            },
            "b",
            ax2,
            colors
    )
    
    fig.tight_layout()
    utils.saveFig(filename)
    
    # Create the stand-alone legend.
    utils.drawLegendRect(
            [
                "uncompr.\nuncompr.",
                "uncompr.\nstatic BP",
                "static BP\nstatic BP",
                "DELTA + SIMD-BP\nstatic BP",
                "FOR + SIMD-BP\nstatic BP"
            ],
            colors
    )
    utils.saveFig(filename + "_legend")

# *****************************************************************************
# Main program
# *****************************************************************************

if __name__ == "__main__":
    # -------------------------------------------------------------------------
    # Argument parsing
    # -------------------------------------------------------------------------
    
    # Defaults.
    processingStyle = pss.PS_VEC512
    countReps = 10
    useExample = True
    useSingleOp = True
    useSimpleQuery = True
    
    # Set up the parser.
    # TODO Provide help messages.
    parser = argparse.ArgumentParser(description=__doc__)
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
    gr = parser.add_mutually_exclusive_group()
    gr.add_argument(
            "--onlyExample", action="store_true",
            help="",
            default=False
    )
    gr.add_argument(
            "--onlySingleOp", action="store_true",
            help="",
            default=False
    )
    gr.add_argument(
            "--onlySimpleQuery", action="store_true",
            help="",
            default=False
    )
    
    # Parse arguments.
    args = parser.parse_args()
    processingStyle = args.processingStyle
    countReps = args.repetitions
    if args.onlyExample:
        useSingleOp = False
        useSimpleQuery = False
    elif args.onlySingleOp:
        useExample = False
        useSimpleQuery = False
    elif args.onlySimpleQuery:
        useExample = False
        useSingleOp = False
    
    # Validate arguments.
    # TODO
    
    # -------------------------------------------------------------------------
    # Setting the paths to certain artifacts
    # -------------------------------------------------------------------------
    
    pathArtifacts = os.path.join("artifacts", "microbenchmarks")
    
    # -------------------------------------------------------------------------
    # Some more settings
    # -------------------------------------------------------------------------
    
    # For Figure 4.
    VAR_UU = "uncompressed operator\nuncompressed data"
    VAR_OTFDRC = "on-the-fly de/re-compression\nStatic BP (3-bit)"
    VAR_SPEC = "BW/H (specialized operator)\nStatic BP (4-bit)"
    VAR_OTFM = "on-the-fly morphing + BW/H\nStatic BP (3-bit)"
    variantMap = {
        "uncompressed"         : VAR_UU,
        "otf de/re-compression": VAR_OTFDRC,
        "specialized"          : VAR_SPEC,
        "otf morphing"         : VAR_OTFM,
    }
    
    # -------------------------------------------------------------------------
    # Load the measurements
    # -------------------------------------------------------------------------
    
    print("Loading measurements... ", end="")
    sys.stdout.flush()

    if useExample:
        dfMeaFigure4 = loadMeaFigure4()
    if useSingleOp:
        dfMeaFigure5 = loadMeaFigure5()
    if useSimpleQuery:
        dfMeaFigure6 = loadMeaFigure6()
        
    print("done.")
    
    # -------------------------------------------------------------------------
    # Diagram generation
    # -------------------------------------------------------------------------
    
    print("Generating diagrams... ", end="")
    sys.stdout.flush()
    
    sns.set_context("talk")

    utils.pathDias = pathArtifacts
    utils.setMatplotlibRcParamsLikeInJupyterNotebook()

    if useExample:
        drawFigure4(dfMeaFigure4, 1 / 10000)
    if useSingleOp:
        drawFigure5(dfMeaFigure5)
    if useSimpleQuery:
        drawFigure6(dfMeaFigure6)
    
    print("done.")