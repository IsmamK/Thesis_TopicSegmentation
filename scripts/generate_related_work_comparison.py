"""Generate a detailed related-work comparison table for LECSEG positioning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _latex_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\scriptsize",
        r"\setlength{\tabcolsep}{3pt}",
        r"\renewcommand{\arraystretch}{1.08}",
        r"\caption{Detailed comparison with related lecture/video chaptering work. Metrics are not directly interchangeable across datasets.}",
        r"\label{tab:related_work_detailed}",
        r"\begin{tabularx}{\linewidth}{p{0.17\linewidth}p{0.10\linewidth}p{0.18\linewidth}X p{0.22\linewidth}}",
        r"\toprule",
        " & ".join(_latex_escape(h) for h in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(_latex_escape(cell) for cell in row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table}"])
    return "\n".join(lines)


def build_rows() -> list[dict[str, Any]]:
    significance = _read_json(ROOT / "results" / "method_selector_significance.json")
    selector = significance["summary"]["selector"]
    current = significance["summary"]["current"]
    baseline = significance["summary"]["baseline"]

    return [
        {
            "work": "LECSEG-30 balanced selector (ours)",
            "url": "",
            "videos": "30",
            "supervision": "Low-resource leave-one-video-out method selection over local candidates",
            "metrics": "Pk, WD, BS, F1@2",
            "reported_result": (
                f"Pk={_fmt(selector['pk'])}, WD={_fmt(selector['wd'])}, "
                f"BS={_fmt(selector['boundary_similarity'])}, F1@2={_fmt(selector['f1_tol2'])}"
            ),
            "lecseg_position": "Reference result; significant Pk/WD gain vs BGE-divisive, not significant vs cross-model on Pk/WD.",
        },
        {
            "work": "LECSEG-30 cross-model conservative (ours)",
            "url": "",
            "videos": "30",
            "supervision": "Unsupervised/conservative cross-model agreement",
            "metrics": "Pk, WD, BS, F1@2",
            "reported_result": (
                f"Pk={_fmt(current['pk'])}, WD={_fmt(current['wd'])}, "
                f"BS={_fmt(current['boundary_similarity'])}, F1@2={_fmt(current['f1_tol2'])}"
            ),
            "lecseg_position": "Strongest statistically supported Pk/WD improvement over BGE-divisive baseline.",
        },
        {
            "work": "BGE-divisive baseline (ours)",
            "url": "",
            "videos": "30",
            "supervision": "Unsupervised text-embedding divisive segmentation",
            "metrics": "Pk, WD, BS, F1@2",
            "reported_result": (
                f"Pk={_fmt(baseline['pk'])}, WD={_fmt(baseline['wd'])}, "
                f"BS={_fmt(baseline['boundary_similarity'])}, F1@2={_fmt(baseline['f1_tol2'])}"
            ),
            "lecseg_position": "Implemented baseline used for local significance claims.",
        },
        {
            "work": "MiniSeg / YTSEG",
            "url": "https://arxiv.org/abs/2402.17633",
            "videos": "19,299",
            "supervision": "Supervised smart-chaptering benchmark/model",
            "metrics": "Boundary P/R/F1, Pk, BS",
            "reported_result": "YTSEG MiniSeg: P=45.44, R=41.48, F1=43.37, Pk=28.73, BS=35.74.",
            "lecseg_position": "External method is stronger on scale and Pk; LECSEG is stronger only as a small lecture-specific hierarchy/reproducibility artifact.",
        },
        {
            "work": "Chapter-Gen / multimodal video chapter generation",
            "url": "https://arxiv.org/abs/2209.12694",
            "videos": "9,631",
            "supervision": "Supervised localization and title generation",
            "metrics": "AP, Recall@3s/5s, ROUGE",
            "reported_result": "Visual+text localization AP=43.3, Recall@3s=60.1, Recall@5s=76.1.",
            "lecseg_position": "External method is stronger for supervised chapter localization; metrics differ from Pk/WD.",
        },
        {
            "work": "VidChapters-7M",
            "url": "https://antoyang.github.io/vidchapters.html",
            "videos": "817,000",
            "supervision": "Large-scale video-language pretraining/finetuning benchmark",
            "metrics": "SODA_c, CIDEr, METEOR, R/P@seconds and IoU",
            "reported_result": "817K videos, 7M chapters; Vid2Seq speech+visual full generation SODA_c=11.4.",
            "lecseg_position": "External benchmark is far stronger in scale; LECSEG is not comparable as a best-system claim.",
        },
        {
            "work": "Chapter-Llama",
            "url": "https://openaccess.thecvf.com/content/CVPR2025/papers/Ventura_Chapter-Llama_Efficient_Chaptering_in_Hour-Long_Videos_with_LLMs_CVPR_2025_paper.pdf",
            "videos": "10,000 train / 8,100 test",
            "supervision": "Trained long-context LLM chapterer",
            "metrics": "Chapter F1, tIoU, SODA/CIDEr-style scores",
            "reported_result": "VidChapters-7M test: Chapter-Llama F1=45.3 vs Vid2Seq F1=26.7.",
            "lecseg_position": "External method is much stronger; motivates learned reranking rather than an external-best LECSEG claim.",
        },
        {
            "work": "TreeSeg / TinyRec",
            "url": "https://arxiv.org/abs/2407.12028",
            "videos": "21",
            "supervision": "Unsupervised hierarchical transcript segmentation",
            "metrics": "Pk, WD on transcript corpora",
            "reported_result": "TinyRec Pk=0.367; ICSI Pk=0.310, WD=0.353; AMI Pk=0.355, WD=0.396.",
            "lecseg_position": "Closest small unsupervised comparator; LECSEG is not a clean winner without a shared benchmark rerun.",
        },
        {
            "work": "AVLectures",
            "url": "https://arxiv.org/abs/2210.16644",
            "videos": "2,350+",
            "supervision": "Self-supervised/audio-visual representation and clustering resource",
            "metrics": "Task-specific lecture-understanding metrics",
            "reported_result": "86 STEM courses and 2,350+ lectures for audio-visual academic video understanding.",
            "lecseg_position": "Stronger lecture-video scale; LECSEG is stronger only for explicit Pk/WD chapter segmentation and hierarchy.",
        },
    ]


def build_markdown(rows: list[dict[str, Any]]) -> str:
    headers = ["Work", "Videos", "Supervision", "Metrics", "Reported result", "LECSEG verdict"]
    table_rows = [
        [
            row["work"] if not row["url"] else f"[{row['work']}]({row['url']})",
            row["videos"],
            row["supervision"],
            row["metrics"],
            row["reported_result"],
            row["lecseg_position"],
        ]
        for row in rows
    ]
    source_lines = [
        "- MiniSeg/YTSEG: https://arxiv.org/abs/2402.17633",
        "- Chapter-Gen: https://arxiv.org/abs/2209.12694",
        "- VidChapters-7M: https://antoyang.github.io/vidchapters.html and https://arxiv.org/abs/2309.13952",
        "- Chapter-Llama: https://openaccess.thecvf.com/content/CVPR2025/papers/Ventura_Chapter-Llama_Efficient_Chaptering_in_Hour-Long_Videos_with_LLMs_CVPR_2025_paper.pdf",
        "- TreeSeg: https://arxiv.org/abs/2407.12028",
        "- AVLectures: https://arxiv.org/abs/2210.16644",
    ]
    return "\n".join(
        [
            "# Detailed Related-Work Comparison",
            "",
            "Generated by `python scripts/generate_related_work_comparison.py`.",
            "The rows are for positioning only; datasets and metrics are not directly interchangeable.",
            "",
            _markdown_table(headers, table_rows),
            "",
            "## Safe Interpretation",
            "",
            "LECSEG is stronger on lecture-specific reproducibility, hierarchy, and local statistical analysis.",
            "Large supervised chaptering systems remain stronger on scale and reported external benchmark performance.",
            "",
            "## Sources",
            "",
            *source_lines,
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=ROOT / "results" / "related_work_comparison.json")
    parser.add_argument("--docs-output", type=Path, default=ROOT / "docs" / "RELATED_WORK_COMPARISON.md")
    parser.add_argument("--tex-output", type=Path, default=ROOT / "thesis" / "tables" / "related_work_comparison.tex")
    args = parser.parse_args()

    rows = build_rows()
    args.json_output.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    args.docs_output.write_text(build_markdown(rows), encoding="utf-8")

    headers = ["Work", "Videos", "Supervision", "Metric/result", "LECSEG verdict"]
    latex_rows = [
        [
            "LECSEG balanced selector",
            "30",
            "LOO method selector",
            "Pk=0.3588; WD=0.3739; F1@2=0.0893",
            "Reference low-resource result.",
        ],
        [
            "MiniSeg/YTSEG",
            "19,299",
            "Supervised",
            "Pk=28.73; BS=35.74; F1=43.37",
            "External method stronger on scale/Pk.",
        ],
        [
            "Chapter-Gen",
            "9,631",
            "Supervised multimodal",
            "AP=43.3; R@5s=76.1",
            "Stronger supervised localization.",
        ],
        [
            "VidChapters-7M",
            "817,000",
            "Large-scale finetuned",
            "7M chapters; SODA_c=11.4",
            "Far stronger scale.",
        ],
        [
            "Chapter-Llama",
            "10k/8.1k",
            "Trained LLM",
            "F1=45.3 vs Vid2Seq 26.7",
            "Stronger trained chapterer.",
        ],
        [
            "TreeSeg/TinyRec",
            "21",
            "Unsupervised",
            "TinyRec Pk=0.367",
            "Closest small comparator; no shared-run win.",
        ],
        [
            "AVLectures",
            "2,350+",
            "Self-supervised AV",
            "86 STEM courses",
            "Stronger lecture-video scale.",
        ],
    ]
    args.tex_output.parent.mkdir(parents=True, exist_ok=True)
    args.tex_output.write_text(_latex_table(headers, latex_rows), encoding="utf-8")

    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.docs_output}")
    print(f"Wrote {args.tex_output}")


if __name__ == "__main__":
    main()
