"""
Build the dataset LaTeX table for thesis Appendix A from manifest.jsonl.

Usage:
    python scripts/build_dataset_table.py
    python scripts/build_dataset_table.py --output thesis/appendices/generated_table.tex
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOMAIN_SHORT = {
    "CS": "CS",
    "MATH": "Math",
    "PHYSICS": "Physics",
    "BIOLOGY": "Biology",
    "HUMANITIES": "Hum.",
    "PHILOSOPHY": "Phil.",
}


def load_manifest() -> list[dict]:
    p = ROOT / "data" / "manifest.jsonl"
    records = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return sorted(records, key=lambda r: r["id"])


def load_gt(video_id: str) -> dict:
    p = ROOT / "data" / "gt" / f"{video_id}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def build_table(records: list[dict]) -> str:
    lines = [
        r"\begin{table}[h]",
        r"  \centering",
        r"  \caption{\dataset{} video list (30 videos). Duration rounded to nearest minute.}",
        r"  \label{tab:video_list}",
        r"  \scriptsize",
        r"  \begin{tabular}{llrr}",
        r"    \toprule",
        r"    Video ID & Domain & Dur.\ (min) & \# Chapters \\",
        r"    \midrule",
    ]

    domain_counts: dict[str, int] = {}
    total_dur_min = 0
    total_chapters = 0

    for r in records:
        vid = r["id"]
        domain = DOMAIN_SHORT.get(r.get("domain", ""), r.get("domain", "?"))
        dur_min = round(r.get("duration_sec", 0) / 60)
        n_ch = r.get("num_chapters", "?")
        total_dur_min += dur_min
        if isinstance(n_ch, int):
            total_chapters += n_ch
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # Escape underscores in video IDs
        vid_tex = vid.replace("_", r"\_").replace("-", r"\mbox{-}")
        lines.append(f"    {vid_tex} & {domain} & {dur_min} & {n_ch} \\\\")

    lines += [
        r"    \midrule",
        f"    Total & {len(records)} videos & {total_dur_min} & {total_chapters} \\\\",
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]

    # Domain summary as a separate mini-table
    lines += [
        "",
        r"\begin{table}[h]",
        r"  \centering",
        r"  \caption{Domain distribution of \dataset{}.}",
        r"  \label{tab:domain_dist}",
        r"  \begin{tabular}{lr}",
        r"    \toprule",
        r"    Domain & \# Videos \\",
        r"    \midrule",
    ]
    for dom, cnt in sorted(domain_counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {dom} & {cnt} \\\\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Build dataset LaTeX table")
    parser.add_argument("--output", default=None, help="Output .tex path (default: stdout)")
    args = parser.parse_args()

    records = load_manifest()
    table = build_table(records)

    if args.output:
        Path(args.output).write_text(table, encoding="utf-8")
        print(f"Written to {args.output}")
    else:
        sys.stdout.write(table + "\n")


if __name__ == "__main__":
    main()
