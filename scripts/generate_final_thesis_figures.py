"""Generate polished, authoritative figures for the final thesis."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "thesis" / "figures"

COLORS = {
    "baseline": "#9aa0a6",
    "cross": "#3b82f6",
    "selector": "#0f9d76",
}


def _load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def final_results() -> None:
    report = _load("results/method_selector_significance.json")["summary"]
    methods = [
        ("BGE-divisive", report["baseline"], COLORS["baseline"]),
        ("Cross-model", report["current"], COLORS["cross"]),
        ("Balanced selector", report["selector"], COLORS["selector"]),
    ]
    metrics = [("Pk", "pk"), ("WindowDiff", "wd"), ("F1@2", "f1_tol2")]
    x = np.arange(len(metrics))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    for index, (label, values, color) in enumerate(methods):
        bars = ax.bar(
            x + (index - 1) * width,
            [values[key] for _, key in metrics],
            width,
            label=label,
            color=color,
        )
        ax.bar_label(bars, fmt="%.3f", fontsize=8, padding=2)
    ax.set_xticks(x, [label for label, _ in metrics])
    ax.set_ylabel("Score")
    ax.set_ylim(0, 0.46)
    ax.legend(frameon=False, ncols=3, loc="upper center")
    fig.tight_layout()
    fig.savefig(OUT / "fig_final_results.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_final_results.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def domain_performance() -> None:
    rows = {
        row["domain"]: row
        for row in _load("results/domain_performance_analysis.json")["rows"]
    }
    domains = ["BIOLOGY", "CS", "MATH", "PHILOSOPHY", "PHYSICS"]
    labels = ["Biology", "CS", "Math", "Philosophy", "Physics"]
    x = np.arange(len(domains))
    width = 0.24
    fig, ax = plt.subplots(figsize=(8.2, 4.2))
    series = [
        ("BGE-divisive", "baseline", COLORS["baseline"]),
        ("Cross-model", "current", COLORS["cross"]),
        ("Balanced selector", "selector", COLORS["selector"]),
    ]
    for index, (label, key, color) in enumerate(series):
        ax.bar(
            x + (index - 1) * width,
            [rows[domain][key]["pk"] for domain in domains],
            width,
            label=label,
            color=color,
        )
    ax.set_xticks(x, labels)
    ax.set_ylabel(r"$P_k$ (lower is better)")
    ax.set_ylim(0, 0.5)
    ax.legend(frameon=False, ncols=3, loc="upper center")
    fig.tight_layout()
    fig.savefig(OUT / "fig_domain_performance.pdf", bbox_inches="tight")
    fig.savefig(OUT / "fig_domain_performance.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _style()
    final_results()
    domain_performance()
    print(f"wrote final thesis figures to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
