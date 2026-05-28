"""
T11 — Extract ground-truth chapter timestamps from all info.json files.

Usage:
    python scripts/extract_gt.py

Writes:
    data/gt/<video_id>.json      — per-video ground truth
    data/gt/gt_summary.csv       — summary table
    data/gt/flags_decisions.md   — pre-populated flagged video list for Fahmida
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.data.gt_from_info import extract_all

console = Console()


def main() -> None:
    console.print("[bold]T11 — Extracting ground-truth chapter timestamps…[/bold]\n")

    flags = extract_all(
        raw_dir=ROOT / "data" / "raw",
        gt_dir=ROOT / "data" / "gt",
    )

    # Count outputs
    gt_files = list((ROOT / "data" / "gt").glob("*.json"))
    console.print(f"[green]Wrote {len(gt_files)} gt.json files[/green]")
    console.print(f"[green]Wrote data/gt/gt_summary.csv[/green]")

    # Print flagged videos
    if flags:
        console.print(f"\n[yellow bold]FLAGS: {len(flags)} flag(s) - review needed:[/yellow bold]")
        tbl = Table("video_id", "reason", show_lines=True)
        for f in flags:
            tbl.add_row(f.video_id, f.reason)
        console.print(tbl)
        _write_flags_md(flags, ROOT / "data" / "gt" / "flags_decisions.md")
        console.print("\n[dim]Flags saved to data/gt/flags_decisions.md — Fahmida to review.[/dim]")
    else:
        console.print("[green]No flags — all videos passed sanity checks.[/green]")

    console.print("\n[bold]Done.[/bold] Next: python scripts/mark_done.py T11")


def _write_flags_md(flags, path: Path) -> None:
    if path.exists():
        return  # don't overwrite manual decisions
    lines = [
        "# GT Flags — Decisions\n",
        "Review each flagged video. For each, write your decision in the Decision column.\n",
        "Options: **keep** / **replace** (go back to T09) / **fix** (edit info.json by hand)\n\n",
        "| video_id | flag | decision | notes |\n",
        "|---|---|---|---|\n",
    ]
    for f in flags:
        lines.append(f"| {f.video_id} | {f.reason} | TBD | |\n")
    path.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
