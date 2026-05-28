"""
Visualisation utilities for segmentation results.

Used for thesis figures and the Streamlit demo (T39).
All functions return matplotlib Figure objects (or None if matplotlib not available).

Usage:
    from lecseg.viz.plots import plot_boundary_scores, plot_segmentation, plot_metrics_table
"""

from __future__ import annotations

from typing import Sequence


def _check_mpl():
    try:
        import matplotlib
        return True
    except ImportError:
        return False


def plot_boundary_scores(
    gap_scores: Sequence[float],
    boundaries: list[int] | None = None,
    reference: list[int] | None = None,
    title: str = "Boundary Gap Scores",
    figsize: tuple[float, float] = (12, 3),
):
    """
    Plot boundary gap scores with predicted and reference boundaries.

    Args:
        gap_scores:  gap score at each sentence boundary (N-1 values)
        boundaries:  predicted boundary indices (1-based)
        reference:   reference boundary indices (1-based)
        title:       figure title
        figsize:     figure size

    Returns:
        matplotlib Figure or None if matplotlib not available.
    """
    if not _check_mpl():
        return None
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=figsize)
    x = list(range(1, len(gap_scores) + 1))
    ax.plot(x, gap_scores, color="steelblue", linewidth=1.5, label="Gap score")
    ax.fill_between(x, gap_scores, alpha=0.2, color="steelblue")

    if boundaries:
        for b in boundaries:
            ax.axvline(b, color="red", linewidth=1.5, linestyle="--",
                       label="Predicted" if b == boundaries[0] else "")

    if reference:
        for r in reference:
            ax.axvline(r, color="green", linewidth=1.5, linestyle="-",
                       label="Reference" if r == reference[0] else "")

    ax.set_xlabel("Sentence gap")
    ax.set_ylabel("Boundary score")
    ax.set_title(title)
    ax.legend(loc="upper right")
    fig.tight_layout()
    return fig


def plot_segmentation(
    sentences: list[str],
    boundaries: list[int],
    reference: list[int] | None = None,
    titles: list[str] | None = None,
    max_chars: int = 60,
    figsize: tuple[float, float] = (14, 6),
):
    """
    Plot a text segmentation as a colour-coded sentence timeline.

    Args:
        sentences:  list of sentence strings
        boundaries: predicted boundary indices (1-based)
        reference:  reference boundaries (shown as dashed lines)
        titles:     segment titles (one per predicted segment)
        max_chars:  truncate sentences to this length for display
        figsize:    figure size

    Returns:
        matplotlib Figure or None.
    """
    if not _check_mpl():
        return None
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    N = len(sentences)
    bounds = [0] + sorted(boundaries) + [N]
    n_segs = len(bounds) - 1
    colors = plt.cm.tab20.colors

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, N)
    ax.set_ylim(-0.5, 0.5)

    for si in range(n_segs):
        lo, hi = bounds[si], bounds[si + 1]
        color = colors[si % len(colors)]
        rect = mpatches.Rectangle(
            (lo, -0.4), hi - lo, 0.8,
            facecolor=color, edgecolor="white", linewidth=1.5, alpha=0.7
        )
        ax.add_patch(rect)
        mid = (lo + hi) / 2
        label = titles[si] if titles and si < len(titles) else f"Seg {si + 1}"
        if len(label) > 20:
            label = label[:18] + "…"
        ax.text(mid, 0, label, ha="center", va="center", fontsize=7, wrap=True)

    if reference:
        for r in reference:
            ax.axvline(r, color="black", linewidth=1.5, linestyle=":", alpha=0.6)

    ax.set_xlabel("Sentence index")
    ax.set_yticks([])
    ax.set_title("Segmentation Visualisation")
    fig.tight_layout()
    return fig


def plot_metrics_table(
    summary: dict[str, dict[str, float]],
    metrics: list[str] | None = None,
    figsize: tuple[float, float] = (10, 4),
):
    """
    Plot an evaluation metrics table as a heatmap.

    Args:
        summary:  {method: {metric: value}}
        metrics:  metric names to include
        figsize:  figure size

    Returns:
        matplotlib Figure or None.
    """
    if not _check_mpl():
        return None
    import matplotlib.pyplot as plt
    import numpy as np

    if metrics is None:
        metrics = ["pk", "wd", "boundary_similarity", "f1"]

    methods = list(summary.keys())
    data = np.array([
        [summary[m].get(metric, float("nan")) for metric in metrics]
        for m in methods
    ])

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn_r")

    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics, rotation=45, ha="right")
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods)

    for i in range(len(methods)):
        for j in range(len(metrics)):
            val = data[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                        fontsize=9, color="black")

    plt.colorbar(im, ax=ax, fraction=0.046)
    ax.set_title("Evaluation Metrics by Method")
    fig.tight_layout()
    return fig
