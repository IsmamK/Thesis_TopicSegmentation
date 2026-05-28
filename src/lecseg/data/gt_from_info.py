"""
Extract ground-truth chapter timestamps from yt-dlp info.json files.

Exists because raw info.json files contain many fields we don't need; this
module distils only the chapter boundaries into a clean, reproducible format
that every downstream evaluation script can depend on.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import NamedTuple


GT_DIR = Path("data/gt")
RAW_DIR = Path("data/raw")

# Sanity-check thresholds
MIN_CHAPTERS = 3
MIN_CHAPTER_SEC = 30
MAX_CHAPTER_SEC = 30 * 60  # 30 minutes


class GTRecord(NamedTuple):
    video_id: str
    boundaries_sec: list[float]
    titles: list[str]
    num_chapters: int
    duration_sec: float


class Flag(NamedTuple):
    video_id: str
    reason: str


# ---------------------------------------------------------------------------
# Parse one info.json
# ---------------------------------------------------------------------------

def parse_info_json(info_path: Path) -> GTRecord | None:
    info = json.loads(info_path.read_text(encoding="utf-8"))
    chapters = info.get("chapters") or []
    duration = float(info.get("duration") or 0)
    video_id = info_path.parent.name

    if not chapters:
        return None

    chapters_sorted = sorted(chapters, key=lambda c: c["start_time"])
    titles = [c["title"] for c in chapters_sorted]
    # boundaries = start times of all chapters EXCEPT the first (t=0 excluded)
    boundaries_sec = [float(c["start_time"]) for c in chapters_sorted if c["start_time"] > 0]

    return GTRecord(
        video_id=video_id,
        boundaries_sec=boundaries_sec,
        titles=titles,
        num_chapters=len(chapters_sorted),
        duration_sec=duration,
    )


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

def check_flags(rec: GTRecord, chapter_durations: list[float]) -> list[str]:
    reasons = []
    if rec.num_chapters < MIN_CHAPTERS:
        reasons.append(f"only {rec.num_chapters} chapters (min {MIN_CHAPTERS})")
    short = [d for d in chapter_durations if d < MIN_CHAPTER_SEC]
    if short:
        reasons.append(f"{len(short)} chapter(s) shorter than {MIN_CHAPTER_SEC}s")
    long_ = [d for d in chapter_durations if d > MAX_CHAPTER_SEC]
    if long_:
        reasons.append(f"{len(long_)} chapter(s) longer than {MAX_CHAPTER_SEC/60:.0f} min")
    return reasons


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_all(raw_dir: Path = RAW_DIR, gt_dir: Path = GT_DIR) -> list[Flag]:
    gt_dir.mkdir(parents=True, exist_ok=True)
    flags: list[Flag] = []
    summary_rows: list[dict] = []

    info_files = sorted(raw_dir.glob("*/video.info.json"))
    # also catch yt-dlp's alternate naming pattern
    if not info_files:
        info_files = sorted(raw_dir.glob("*/*.info.json"))

    for info_path in info_files:
        rec = parse_info_json(info_path)
        if rec is None:
            flags.append(Flag(info_path.parent.name, "no chapters in info.json"))
            continue

        # Chapter durations
        all_starts = [0.0] + rec.boundaries_sec + [rec.duration_sec]
        chapter_durations = [
            all_starts[i + 1] - all_starts[i]
            for i in range(len(all_starts) - 1)
        ]

        # Save gt.json
        gt_path = gt_dir / f"{rec.video_id}.json"
        gt_path.write_text(
            json.dumps(
                {
                    "video_id": rec.video_id,
                    "boundaries_sec": rec.boundaries_sec,
                    "titles": rec.titles,
                    "num_chapters": rec.num_chapters,
                    "duration_sec": rec.duration_sec,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Sanity flags
        flag_reasons = check_flags(rec, chapter_durations)
        if flag_reasons:
            for r in flag_reasons:
                flags.append(Flag(rec.video_id, r))

        avg_min = (sum(chapter_durations) / len(chapter_durations)) / 60
        summary_rows.append(
            {
                "video_id": rec.video_id,
                "num_chapters": rec.num_chapters,
                "duration_sec": round(rec.duration_sec, 1),
                "avg_chapter_min": round(avg_min, 2),
                "min_chapter_min": round(min(chapter_durations) / 60, 2),
                "max_chapter_min": round(max(chapter_durations) / 60, 2),
            }
        )

    # Write summary CSV
    if summary_rows:
        csv_path = gt_dir / "gt_summary.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["video_id", "num_chapters", "duration_sec",
                            "avg_chapter_min", "min_chapter_min", "max_chapter_min"],
            )
            writer.writeheader()
            writer.writerows(summary_rows)

    return flags
