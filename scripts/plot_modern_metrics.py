"""Generate thesis figures from modern metric artifacts."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "results" / "modern_metrics_summary.csv"
OUT_DIRS = [ROOT / "figures", ROOT / "thesis" / "figures"]


def _rows() -> list[dict[str, str]]:
    with SUMMARY.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _save(fig: plt.Figure, name: str) -> None:
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight")
        fig.savefig(out_dir / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_structure_vs_boundary(rows: list[dict[str, str]]) -> None:
    labels = [r["label"] for r in rows]
    pk = np.array([float(r["pk"]) for r in rows])
    f1_2 = np.array([float(r["sent_f1_t2"]) for r in rows])
    f1_10 = np.array([float(r["sent_f1_t10"]) for r in rows])

    order = np.argsort(pk)
    labels = [labels[i] for i in order]
    pk = pk[order]
    f1_2 = f1_2[order]
    f1_10 = f1_10[order]

    x = np.arange(len(labels))
    width = 0.26
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(x - width, pk, width, label="Pk (lower better)", color="#2f5d8c")
    ax.bar(x, f1_2, width, label="F1@2 sentences", color="#b84a39")
    ax.bar(x + width, f1_10, width, label="F1@10 sentences", color="#4f8a5b")
    ax.set_ylabel("Metric value")
    ax.set_title("Structure Quality vs Exact Boundary Hits")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=22, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    _save(fig, "modern_metrics_structure_vs_f1")


def plot_boundary_count(rows: list[dict[str, str]]) -> None:
    labels = [r["label"] for r in rows]
    count_err = np.array([float(r["count_error"]) for r in rows])
    abs_err = np.array([float(r["abs_count_error"]) for r in rows])
    order = np.argsort(abs_err)
    labels = [labels[i] for i in order]
    count_err = count_err[order]

    colors = ["#2f5d8c" if v <= 0 else "#b84a39" for v in count_err]
    fig, ax = plt.subplots(figsize=(10.5, 5))
    ax.barh(labels, count_err, color=colors)
    ax.axvline(0, color="#222222", linewidth=1)
    ax.set_xlabel("Predicted boundaries minus reference boundaries")
    ax.set_title("Boundary Count Error Explains F1/Pk Tradeoffs")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    _save(fig, "modern_metrics_boundary_count_error")


def plot_segment_overlap(rows: list[dict[str, str]]) -> None:
    labels = [r["label"] for r in rows]
    tiou = np.array([float(r["mean_best_tiou"]) for r in rows])
    time_f1 = np.array([float(r["time_f1_30s"]) for r in rows])
    order = np.argsort(-tiou)
    labels = [labels[i] for i in order]
    tiou = tiou[order]
    time_f1 = time_f1[order]

    x = np.arange(len(labels))
    width = 0.34
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - width / 2, tiou, width, label="Mean best tIoU", color="#5a4f8a")
    ax.bar(x + width / 2, time_f1, width, label="F1@30s", color="#c0802f")
    ax.set_ylabel("Metric value")
    ax.set_title("Video-Oriented Boundary and Segment Metrics")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=22, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    _save(fig, "modern_metrics_time_segment")


def main() -> None:
    rows = _rows()
    plot_structure_vs_boundary(rows)
    plot_boundary_count(rows)
    plot_segment_overlap(rows)
    print("Wrote modern metric figures to figures/ and thesis/figures/")


if __name__ == "__main__":
    main()
