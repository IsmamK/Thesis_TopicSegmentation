"""
Download transcripts from vast.ai and optionally destroy the instance.

Run after all 30 transcriptions complete:
    python scripts/download_transcripts.py

Or to just check without downloading:
    python scripts/download_transcripts.py --check-only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "transcripts"

# vast.ai instance connection details
HOST = "154.12.38.116"
PORT = 21115
REMOTE_DIR = "/workspace/transcripts/"
KEY = f"{Path.home()}/.ssh/id_rsa"

SSH_OPTS = "-o StrictHostKeyChecking=no"


def _ssh(cmd: str) -> str:
    """Run a command on the remote instance and return stdout."""
    result = subprocess.run(
        ["ssh", SSH_OPTS, "-i", KEY, "-p", str(PORT), f"root@{HOST}", cmd],
        capture_output=True, text=True
    )
    return result.stdout.strip()


def check_progress() -> tuple[int, list[str]]:
    """Return (n_done, list_of_done_video_ids)."""
    raw = _ssh(f"ls {REMOTE_DIR} 2>/dev/null")
    if not raw:
        return 0, []
    vids = [v.strip() for v in raw.split("\n") if v.strip()]
    return len(vids), vids


def download(out_dir: Path = OUT_DIR) -> bool:
    """SCP all transcripts to local out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "scp", SSH_OPTS, "-i", KEY,
        "-P", str(PORT),
        "-r",
        f"root@{HOST}:{REMOTE_DIR}",
        str(out_dir),
    ]
    print(f"Downloading transcripts to {out_dir}...")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        # Count what we got
        downloaded = list(out_dir.glob("*/transcript.json"))
        print(f"Downloaded {len(downloaded)} transcripts.")
        return True
    else:
        print("Download failed.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download vast.ai transcripts")
    parser.add_argument("--check-only", action="store_true",
                        help="Only check progress, do not download")
    parser.add_argument("--out", default=str(OUT_DIR), help="Local output directory")
    args = parser.parse_args()

    n_done, vids = check_progress()
    print(f"Remote transcripts: {n_done}/30")
    for v in vids:
        print(f"  {v}")

    if args.check_only:
        return

    if n_done < 30:
        ans = input(f"\nOnly {n_done}/30 done. Download anyway? [y/N] ")
        if ans.lower() != "y":
            print("Cancelled.")
            return

    success = download(Path(args.out))

    if success:
        print("\nTranscripts downloaded successfully.")
        print("\nNEXT STEPS:")
        print("1. Destroy the vast.ai instance to stop billing!")
        print("   (go to https://vast.ai and destroy instance)")
        print("2. Run sentence splitting:")
        print("   python src/lecseg/preprocess/sentence_split.py")
        print("3. Run autoannotate (Ollama must be running):")
        print("   python scripts/autoannotate.py")
        print("4. Review annotations:")
        print("   streamlit run scripts/annotate.py")


if __name__ == "__main__":
    main()
