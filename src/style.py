"""Shared chart style: one palette and one look for every figure in the project."""
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_MUTED = "#52514e"
GRID = "#e4e3df"

# Categorical slots, always in this order. 7-Eleven is always slot 1.
SEVEN_ELEVEN = "#2a78d6"
REST = "#eb6834"
THIRD = "#1baf7a"
FOURTH = "#eda100"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_MUTED,
    "axes.titlecolor": TEXT,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": TEXT_MUTED,
    "ytick.color": TEXT_MUTED,
    "lines.linewidth": 2,
    "legend.frameon": False,
    "legend.labelcolor": TEXT,
    "font.size": 10.5,
})


def label_end(ax, x, y, text, color):
    """Direct label at the end of a line, in text ink with a colored marker."""
    ax.plot([x], [y], "o", color=color, markersize=6, markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax.annotate(text, (x, y), xytext=(8, 0), textcoords="offset points",
                va="center", color=TEXT, fontsize=10)
