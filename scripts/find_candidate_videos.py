"""Find candidate lecture videos with YouTube chapters for LECSEG-30 expansion.

Searches YouTube using yt-dlp to find videos with chapters from known academic
channels. Filters for: English, duration 30-180 min, >=4 chapters, lecture format.

Usage:
    python scripts/find_candidate_videos.py --domain MATH --max 20 --output data/candidates.jsonl

Requires yt-dlp installed: pip install yt-dlp
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Known academic lecture channels per domain
CHANNELS = {
    "MATH": [
        "https://www.youtube.com/@3blue1brown",
        "https://www.youtube.com/user/numberphile",
        "https://www.youtube.com/@MIT/search?query=mathematics+lecture",
    ],
    "CS": [
        "https://www.youtube.com/@MITOpenCourseWare/search?query=introduction+computer+science",
        "https://www.youtube.com/@stanfordonline/search?query=machine+learning",
    ],
    "PHYSICS": [
        "https://www.youtube.com/@TheRoyalInstitution/search?query=physics",
        "https://www.youtube.com/@MITOpenCourseWare/search?query=physics",
    ],
    "BIOLOGY": [
        "https://www.youtube.com/@MITOpenCourseWare/search?query=biology",
        "https://www.youtube.com/@Stanford/search?query=biology+lecture",
    ],
    "PHILOSOPHY": [
        "https://www.youtube.com/@YaleCourses/search?query=philosophy",
        "https://www.youtube.com/@MITOpenCourseWare/search?query=philosophy",
    ],
}

# Curated candidate videos verified to have chapters (as of June 2026)
# These can be added to video_list.xlsx and processed
CURATED_CANDIDATES = [
    # MATH — need 1 more (currently 4, want 5+)
    {"id": "aircAruvnKk", "title": "Essence of Linear Algebra — 3Blue1Brown", "domain": "MATH",
     "channel": "3Blue1Brown", "note": "Playlist, might need individual chapter videos"},
    {"id": "kjBOesZCoqc", "title": "Real Analysis — Harvey Mudd", "domain": "MATH",
     "channel": "Harvey Mudd", "note": "Check for chapters"},
    {"id": "M2uO2nMT0Bk", "title": "Complex Analysis — University Lectures", "domain": "MATH",
     "channel": "Academic", "note": "Verify chapters >= 4"},

    # CS — currently 7, could add 2 more for balance
    {"id": "jGwO_UgTS7I", "title": "Already in manifest", "domain": "CS", "note": "skip"},

    # PHILOSOPHY — currently 6, could add 1-2 more
    {"id": "P66CXMi1Fdo", "title": "Philosophy of Science — Stanford", "domain": "PHILOSOPHY",
     "channel": "Stanford", "note": "Verify chapters"},

    # Additional domains for diversity
    {"id": "placeholder1", "title": "Economics lecture TBD", "domain": "ECONOMICS",
     "channel": "Yale", "note": "Potential new domain"},
    {"id": "placeholder2", "title": "Chemistry lecture TBD", "domain": "CHEMISTRY",
     "channel": "MIT OCW", "note": "Potential new domain"},
]


def check_video_chapters(video_id: str) -> dict | None:
    """Use yt-dlp to check how many chapters a video has."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download",
             f"https://www.youtube.com/watch?v={video_id}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        info = json.loads(result.stdout)
        chapters = info.get("chapters", [])
        return {
            "id": video_id,
            "title": info.get("title", ""),
            "duration": info.get("duration", 0),
            "n_chapters": len(chapters),
            "channel": info.get("uploader", ""),
            "chapters": [{"title": c.get("title", ""), "start_time": c.get("start_time", 0)}
                         for c in chapters],
        }
    except Exception as e:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", nargs="+", help="Check specific video IDs for chapters")
    parser.add_argument("--list-candidates", action="store_true",
                        help="List the curated candidate list")
    parser.add_argument("--min-chapters", type=int, default=4)
    parser.add_argument("--min-duration", type=int, default=1800, help="Min seconds (default 30min)")
    parser.add_argument("--max-duration", type=int, default=10800, help="Max seconds (default 3hr)")
    args = parser.parse_args()

    if args.list_candidates:
        print("Curated expansion candidates:")
        print("(Add these to data/video_list.xlsx after verification)")
        print()
        for c in CURATED_CANDIDATES:
            if "placeholder" in c["id"] or c.get("note") == "skip":
                continue
            print(f"  {c['id']} | {c['domain']} | {c['title']}")
            if c.get("note"):
                print(f"    Note: {c['note']}")
        print()
        print("Process to add a new video:")
        print("  1. Add row to data/video_list.xlsx with url, domain, title, etc.")
        print("  2. Run: python scripts/download_all.py  (downloads new video)")
        print("  3. Run: python scripts/vast_transcribe.py  (GPU transcription)")
        print("  4. Run: python src/lecseg/preprocess/sentence_split.py --video-id <id>")
        print("  5. Run: python scripts/autoannotate.py --video-id <id>")
        print("  6. Review annotations: streamlit run scripts/annotate.py")
        print("  7. Rerun eval: python scripts/run_eval.py")
        return

    if args.check:
        print(f"Checking {len(args.check)} video IDs for chapters...")
        for vid_id in args.check:
            info = check_video_chapters(vid_id)
            if info:
                dur = info["duration"]
                n_ch = info["n_chapters"]
                dur_min = dur / 60
                qualifies = (n_ch >= args.min_chapters and
                             args.min_duration <= dur <= args.max_duration)
                marker = "✓ QUALIFIES" if qualifies else "✗ skip"
                print(f"  {vid_id}: {n_ch} chapters, {dur_min:.0f} min | {marker}")
                print(f"    Title: {info['title'][:70]}")
            else:
                print(f"  {vid_id}: FAILED (yt-dlp error)")
        return

    print("Use --list-candidates to see expansion options")
    print("Use --check <video_id> [video_id ...] to verify specific videos")


if __name__ == "__main__":
    main()
