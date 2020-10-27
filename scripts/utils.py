import os

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.lines as lines

"""
Some utilities required by the diagram generation of both the micro benchmarks
and the Star Schema Benchmark.
"""

# -----------------------------------------------------------------------------
# Utility for saving a figure.
# -----------------------------------------------------------------------------

pathDias = None

def saveFig(filename):
    """Saves the current matplotlib figure to a file."""
    
    if pathDias is None:
        raise RuntimeError("you must set utils.pathDias first")
    
    plt.savefig(
            os.path.join(pathDias, "{}.pdf".format(filename)),
            bbox_inches="tight"
    )
    
# -----------------------------------------------------------------------------
# Utilities for drawing stand-alone legends.
# -----------------------------------------------------------------------------

def drawLegendRect(labels, colors):
    """Generates a legend in an individual matplotlib figure."""

    fig = plt.figure()
    generalRectProps = dict(linewidth=1, edgecolor="black", clip_on=False)
    fig.legend(
        [
            patches.Rectangle((0, 0), 1, 1, **generalRectProps, facecolor=color)
            for color in colors
        ],
        labels,
        ncol=999, frameon=False,
        handlelength=1, columnspacing=1
    )
    
def drawLegendMarker(labels, colors):
    """Generates a legend in an individual matplotlib figure."""

    fig = plt.figure()
    fig.legend(
        [
            lines.Line2D(
                    [0.5], [0.5],
                    linewidth=0,
                    marker="o",
                    markerfacecolor=color,
                    markeredgecolor=color
            )
            for color in colors
        ],
        labels,
        ncol=999, frameon=False,
        handlelength=1, columnspacing=1
    )
    
# -----------------------------------------------------------------------------
# Utility for matplotlib rcParams.
# -----------------------------------------------------------------------------
    
def setMatplotlibRcParamsLikeInJupyterNotebook():
    # We originally created the diagrams in a jupyter notebook. In that
    # environment, some rcParams of matplotlib are different. To obtain
    # exactly the same diagram sizes etc., we explicitly use these rcParams
    # here, but this is not critical for the diagram generation.
    mpl.rcParams["figure.dpi"] = 72.0
    mpl.rcParams["figure.subplot.bottom"] = 0.125
    mpl.rcParams["font.size"] = 10.0