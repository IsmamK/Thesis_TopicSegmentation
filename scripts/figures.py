"""
Generate thesis figures from evaluation results and dataset statistics.

Usage:
    python scripts/figures.py results/eval.json --output figures/
    python scripts/figures.py --dataset-only --output figures/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

METHOD_LABELS = {
    "texttiling":    "TextTiling",
    "c99":           "C99",
    "cosine":        "CosineSeg",
    "kmeans":        "KMeansSeg",
    "bert_seg":      "BertSeg",
    "two_stage":     "TwoStage",
    "two_stage_llm": "TwoStage+LLM",
    "hierarchical":  "Hierarchical",
}

NOVEL_METHODS = {"two_stage", "two_stage_llm", "hierarchical"}
COLORS = {
    "texttiling":    "#aec7e8",
    "c99":           "#ffbb78",
    "cosine":        "#98df8a",
    "kmeans":        "#c5b0d5",
    "bert_seg":      "#f7b6d2",
    "two_stage":     "#1f77b4",
    "two_stage_llm": "#ff7f0e",
    "hierarchical":  "#2ca02c",
}


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


def plot_main_results(results: dict, out_dir: Path):
    """Bar chart of Pk and F1 across all methods."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available; skipping figures")
        return

    methods = [m for m in METHOD_LABELS if m in results]
    labels = [METHOD_LABELS[m] for m in methods]
    colors = [COLORS.get(m, "#888") for m in methods]

    pk_vals  = [_mean([v["pk"] for v in results[m].values() if "pk" in v]) for m in methods]
    f1_vals  = [_mean([v["f1"] for v in results[m].values() if "f1" in v]) for m in methods]

    x = np.arange(len(methods))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    bars1 = ax.bar(x - width/2, pk_vals, width, label=r"$P_k$ (lower=better)", color=colors, alpha=0.85)
    bars2 = ax.bar(x + width/2, f1_vals, width, label=r"$F_1$ (higher=better)",
                   color=colors, alpha=0.5, hatch="//")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Score")
    ax.set_title("Segmentation Performance on LECSEG-30")
    ax.legend()
    ax.axvline(x=len(methods) - len(NOVEL_METHODS) - 0.5, color="gray", linestyle="--", alpha=0.5)
    ax.text(len(methods) - len(NOVEL_METHODS) - 0.3, ax.get_ylim()[1] * 0.95,
            "Ours →", fontsize=8, color="gray")

    fig.tight_layout()
    path = out_dir / "fig_main_results.pdf"
    fig.savefig(str(path), bbox_inches="tight")
    path_png = out_dir / "fig_main_results.png"
    fig.savefig(str(path_png), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def plot_ablation(results: dict, out_dir: Path):
    """Line chart showing incremental gains from N1→N2→N3/N4."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return

    ablation_chain = ["cosine", "two_stage", "hierarchical", "two_stage_llm"]
    chain_labels = ["Baseline\n(CosineSeg)", "+N1+N2\n(TwoStage)", "+N3\n(Hierarchical)", "+N4\n(+LLM)"]

    pk_vals, f1_vals = [], []
    for m in ablation_chain:
        if m not in results:
            pk_vals.append(None)
            f1_vals.append(None)
        else:
            pk_vals.append(_mean([v["pk"] for v in results[m].values() if "pk" in v]))
            f1_vals.append(_mean([v["f1"] for v in results[m].values() if "f1" in v]))

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax2 = ax1.twinx()

    xs = range(len(ablation_chain))
    ax1.plot(xs, pk_vals, "o-", color="#1f77b4", label=r"$P_k$ ↓", linewidth=2)
    ax2.plot(xs, f1_vals, "s--", color="#ff7f0e", label=r"$F_1$ ↑", linewidth=2)

    ax1.set_xticks(list(xs))
    ax1.set_xticklabels(chain_labels, fontsize=9)
    ax1.set_ylabel(r"$P_k$", color="#1f77b4")
    ax2.set_ylabel(r"$F_1$", color="#ff7f0e")
    ax1.set_title("Ablation: Incremental Module Contributions")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right")

    fig.tight_layout()
    path = out_dir / "fig_ablation.pdf"
    fig.savefig(str(path), bbox_inches="tight")
    fig.savefig(str(out_dir / "fig_ablation.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def plot_dataset_stats(out_dir: Path):
    """Dataset statistics figure from GT annotations and video list."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return

    gt_dir = ROOT / "data" / "gt"
    gt_files = [f for f in gt_dir.glob("*.json") if not f.stem.startswith("_")]
    if not gt_files:
        print("No GT files found; skipping dataset figure")
        return

    durations, n_chapters_list = [], []
    for f in gt_files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if "duration_sec" in d:
                durations.append(d["duration_sec"] / 60)  # minutes
            if "boundaries_sec" in d:
                n_chapters_list.append(len(d["boundaries_sec"]) + 1)
        except Exception:
            continue

    if not durations:
        print("No valid GT data; skipping dataset figure")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    axes[0].hist(durations, bins=10, color="#4c72b0", edgecolor="white")
    axes[0].set_xlabel("Duration (minutes)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Video Duration Distribution")

    axes[1].hist(n_chapters_list, bins=range(1, max(n_chapters_list) + 2), color="#55a868", edgecolor="white")
    axes[1].set_xlabel("Number of Chapters")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Chapter Count Distribution")

    fig.suptitle(f"LECSEG-30 Dataset Statistics (n={len(gt_files)} videos)")
    fig.tight_layout()
    path = out_dir / "fig_dataset_stats.pdf"
    fig.savefig(str(path), bbox_inches="tight")
    fig.savefig(str(out_dir / "fig_dataset_stats.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate thesis figures")
    parser.add_argument("results_json", nargs="?", help="Path to results JSON (from run_eval.py)")
    parser.add_argument("--output", default="figures", help="Output directory")
    parser.add_argument("--dataset-only", action="store_true", help="Only generate dataset figures")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_dataset_stats(out_dir)

    if not args.dataset_only:
        if not args.results_json:
            print("results_json required unless --dataset-only", file=sys.stderr)
            sys.exit(1)
        results_path = Path(args.results_json)
        if not results_path.exists():
            print(f"Results file not found: {results_path}", file=sys.stderr)
            sys.exit(1)
        results = json.loads(results_path.read_text(encoding="utf-8"))
        plot_main_results(results, out_dir)
        plot_ablation(results, out_dir)

    print(f"\nAll figures written to {out_dir}/")


if __name__ == "__main__":
    main()
