"""Plan a rollback-safe LECSEG dataset expansion.

The script inspects the current manifest and a candidate video list. It writes a
plan instead of mutating the official benchmark. Use the plan to decide which
videos should be downloaded, transcribed, embedded, and reviewed in a separate
data sprint.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]


def _video_id(url: str) -> str:
    patterns = [
        r"v=([A-Za-z0-9_-]{6,})",
        r"youtu\.be/([A-Za-z0-9_-]{6,})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{6,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return re.sub(r"[^A-Za-z0-9_-]", "_", url)[:24]


def _load_manifest_ids() -> set[str]:
    manifest = ROOT / "data" / "manifest.jsonl"
    ids = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["id"])
    return ids


def _load_video_list() -> list[dict[str, str]]:
    path = ROOT / "data" / "video_list.csv"
    with path.open("rb") as handle:
        magic = handle.read(4)
    if magic != b"PK\x03\x04":
        raise RuntimeError("Expected data/video_list.csv to be the existing xlsx-backed video list")
    import shutil
    import tempfile

    tmp = Path(tempfile.mktemp(suffix=".xlsx"))
    shutil.copy(path, tmp)
    wb = openpyxl.load_workbook(str(tmp), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    out = []
    for row in rows[1:]:
        if not row or row[0] is None:
            continue
        rec = {key: str(value).strip() if value is not None else "" for key, value in zip(header, row)}
        url = rec.get("url", "")
        if url:
            rec["id"] = _video_id(url)
            out.append(rec)
    return out


def main() -> None:
    existing = _load_manifest_ids()
    rows = _load_video_list()
    candidates = [row for row in rows if row["id"] not in existing]
    by_domain: dict[str, int] = {}
    for row in candidates:
        domain = row.get("domain", "").upper() or "UNKNOWN"
        by_domain[domain] = by_domain.get(domain, 0) + 1
    plan = {
        "existing_manifest_videos": len(existing),
        "candidate_rows_in_video_list": len(rows),
        "new_candidates": len(candidates),
        "new_candidates_by_domain": by_domain,
        "next_steps": [
            "Select candidates with creator chapter timestamps.",
            "Download into a separate expansion manifest first.",
            "Transcribe, split sentences, compute embeddings, and extract GT.",
            "Run all official baselines before merging into the thesis benchmark.",
            "Promote to official only after validation and thesis table regeneration.",
        ],
        "candidates": candidates,
    }
    out = ROOT / "results" / "dataset_expansion_plan.json"
    out.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Existing manifest videos: {len(existing)}")
    print(f"New candidate rows: {len(candidates)}")


if __name__ == "__main__":
    main()
