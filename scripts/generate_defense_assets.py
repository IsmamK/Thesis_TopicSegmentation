"""Generate defense-ready oracle-gap and roadmap artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    portfolio = json.loads((ROOT / "results" / "method_portfolio_analysis.json").read_text(encoding="utf-8"))
    low_resource = json.loads((ROOT / "results" / "low_resource_positioning.json").read_text(encoding="utf-8"))
    best = portfolio["best_global"]
    selector = {
        "pk": 0.3588,
        "wd": 0.3739,
        "f1_tol2": 0.0893,
    }
    oracle = portfolio["per_video_oracle"]["metrics"]

    md = ROOT / "docs" / "DEFENSE_ORACLE_GAP.md"
    lines = [
        "# Defense Oracle-Gap Brief\n",
        "\n",
        "Use this as the central defense story: LECSEG is not just a method table; it identifies the next hard problem.\n",
        "\n",
        "## Core Visual\n",
        "\n",
        "| Operating point | Pk | WD | F1@2 | Defense meaning |\n",
        "|---|---:|---:|---:|---|\n",
        f"| Best single global method | {best['pk']:.4f} | {best['wd']:.4f} | {best['f1_tol2']:.4f} | Stable low-resource segmentation |\n",
        f"| Balanced selector | {selector['pk']:.4f} | {selector['wd']:.4f} | {selector['f1_tol2']:.4f} | Best deployable mean Pk/WD operating point |\n",
        f"| Per-video oracle | {oracle['pk']:.4f} | {oracle['wd']:.4f} | {oracle['f1_tol2']:.4f} | Headroom if selection were solved |\n",
        "\n",
        "## Script\n",
        "\n",
        "The key finding is that the candidate/method pool already contains much better decisions than the deployable selector can reliably choose. That means the next research problem is not simply adding more candidate boundaries; it is robust boundary selection under low data.\n",
        "\n",
        "## Low-Resource Scale Line\n",
        "\n",
        "LECSEG uses 30 videos. Large chaptering systems use from thousands to hundreds of thousands of videos, so LECSEG is a low-resource benchmark and diagnostic artifact, not a direct external-best claim.\n",
        "\n",
        "## Defense Slide Spine\n",
        "\n",
        "1. Problem: long lectures need chapter/subtopic navigation.\n",
        "2. Gap: low-resource lecture segmentation lacks compact, auditable hierarchical benchmarks.\n",
        "3. Contribution: LECSEG-30, multimodal pipeline, evaluation suite, diagnostics.\n",
        "4. Result: Pk 0.3588 / WD 0.3739 best deployable operating point.\n",
        "5. Comparison: TreeSeg-style same-dataset baseline does not beat Pk/WD.\n",
        "6. Oracle gap: Pk 0.2980 possible inside the method pool.\n",
        "7. Failure case: Math and selector over-switching.\n",
        "8. Future: 50-video benchmark, LLM comparison, boundary verifier.\n",
    ]
    md.write_text("".join(lines), encoding="utf-8")

    # Simple CSV-like data for plotting or slide creation.
    data = {
        "oracle_gap": [
            {"name": "Cross-model", "pk": best["pk"], "wd": best["wd"], "f1_tol2": best["f1_tol2"]},
            {"name": "Balanced selector", "pk": selector["pk"], "wd": selector["wd"], "f1_tol2": selector["f1_tol2"]},
            {"name": "Oracle", "pk": oracle["pk"], "wd": oracle["wd"], "f1_tol2": oracle["f1_tol2"]},
        ],
        "low_resource_rows": low_resource.get("rows", []),
    }
    out_json = ROOT / "results" / "defense_oracle_gap.json"
    out_json.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        import matplotlib.pyplot as plt

        fig_dir = ROOT / "defense" / "figures"
        fig_dir.mkdir(parents=True, exist_ok=True)
        labels = [row["name"] for row in data["oracle_gap"]]
        pk_vals = [row["pk"] for row in data["oracle_gap"]]
        wd_vals = [row["wd"] for row in data["oracle_gap"]]
        x = range(len(labels))
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        ax.plot(list(x), pk_vals, marker="o", linewidth=2.4, label="Pk")
        ax.plot(list(x), wd_vals, marker="s", linewidth=2.4, label="WindowDiff")
        ax.set_xticks(list(x), labels, rotation=10)
        ax.set_ylim(0.25, 0.40)
        ax.set_ylabel("Lower is better")
        ax.set_title("Oracle Gap: Boundary Selection Is The Bottleneck")
        ax.grid(axis="y", alpha=0.25)
        ax.legend()
        for idx, value in enumerate(pk_vals):
            ax.annotate(f"{value:.3f}", (idx, value), textcoords="offset points", xytext=(0, 8), ha="center")
        fig.tight_layout()
        fig.savefig(fig_dir / "oracle_gap.pdf")
        fig.savefig(fig_dir / "oracle_gap.png", dpi=180)
        plt.close(fig)
    except Exception as exc:
        print(f"Skipped oracle-gap figure generation: {exc}")
    print(f"Wrote {md}")
    print(f"Wrote {out_json}")


if __name__ == "__main__":
    main()
