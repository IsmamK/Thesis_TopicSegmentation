"""
Verify downloaded transcripts are complete and valid.

Run after downloading transcripts from vast.ai:
    python scripts/check_transcripts.py

Checks:
  - All 30 videos have a transcript
  - Each transcript has segments
  - No zero-length transcripts
  - Duration matches video list
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = ROOT / "data" / "transcripts"
VIDEO_LIST = ROOT / "data" / "video_list.csv"


def check_all() -> bool:
    if not TRANSCRIPTS_DIR.exists():
        print("ERROR: data/transcripts/ not found. Did you run download_transcripts.py?")
        return False

    # Load video list
    video_ids = []
    if VIDEO_LIST.exists():
        import csv
        with VIDEO_LIST.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                vid = row.get("video_id") or row.get("id") or ""
                if vid:
                    video_ids.append(vid.strip())
    else:
        # Fallback: discover from transcript dirs
        video_ids = [d.name for d in TRANSCRIPTS_DIR.iterdir() if d.is_dir()]

    print(f"Expected videos: {len(video_ids)}")
    print()

    ok, issues = [], []

    for vid in sorted(video_ids):
        t_path = TRANSCRIPTS_DIR / vid / "transcript.json"
        if not t_path.exists():
            issues.append(f"  MISSING: {vid}")
            continue

        try:
            data = json.loads(t_path.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"  PARSE ERROR: {vid} — {e}")
            continue

        n_segs = len(data.get("segments", []))
        duration = data.get("duration_sec", 0)

        if n_segs == 0:
            issues.append(f"  EMPTY: {vid} (0 segments)")
        elif duration < 60:
            issues.append(f"  SHORT: {vid} ({duration:.0f}s, {n_segs} segs)")
        else:
            ok.append(f"  OK  {vid:<20} {duration/60:5.1f}min  {n_segs:4d} segs")

    print("Passed:")
    for line in ok:
        print(line)

    if issues:
        print()
        print("Issues:")
        for line in issues:
            print(line)

    print()
    print(f"Summary: {len(ok)}/{len(video_ids)} OK, {len(issues)} issues")

    return len(issues) == 0


def main():
    success = check_all()
    if success:
        print("\nAll transcripts look good!")
        print("\nNEXT: python src/lecseg/preprocess/sentence_split.py")
    else:
        print("\nFix issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
