"""Integration tests using data/manifest.jsonl — validate dataset consistency."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "manifest.jsonl"
GT_DIR = ROOT / "data" / "gt"


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST.exists():
        pytest.skip("data/manifest.jsonl not found")
    records = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


@pytest.fixture(scope="module")
def gt_records(manifest):
    records = {}
    for item in manifest:
        vid = item["id"]
        gt_path = GT_DIR / f"{vid}.json"
        if gt_path.exists():
            records[vid] = json.loads(gt_path.read_text(encoding="utf-8"))
    return records


def test_manifest_has_30_entries(manifest):
    assert len(manifest) == 30, f"Expected 30 videos, got {len(manifest)}"


def test_manifest_fields_present(manifest):
    required = {"id", "url", "domain", "title", "duration_sec", "num_chapters"}
    for record in manifest:
        missing = required - set(record.keys())
        assert not missing, f"Missing fields {missing} in {record.get('id')}"


def test_manifest_domains_valid(manifest):
    valid_domains = {"CS", "MATH", "PHYSICS", "BIOLOGY", "HUMANITIES", "PHILOSOPHY"}
    for record in manifest:
        assert record["domain"] in valid_domains, \
            f"{record['id']} has invalid domain: {record['domain']}"


def test_manifest_durations_reasonable(manifest):
    for record in manifest:
        dur = record["duration_sec"]
        assert 300 <= dur <= 50000, \
            f"{record['id']} has unreasonable duration: {dur}s"


def test_manifest_ids_unique(manifest):
    ids = [r["id"] for r in manifest]
    assert len(ids) == len(set(ids)), "Duplicate video IDs in manifest"


def test_manifest_num_chapters_positive(manifest):
    for record in manifest:
        assert record["num_chapters"] >= 2, \
            f"{record['id']} has too few chapters: {record['num_chapters']}"


def test_gt_files_exist_for_manifest(manifest):
    """GT files should exist for videos in the manifest."""
    missing = []
    for record in manifest:
        vid = record["id"]
        gt_path = GT_DIR / f"{vid}.json"
        if not gt_path.exists():
            missing.append(vid)
    # Allow some missing (not all downloaded)
    assert len(missing) <= 5, f"Too many missing GT files: {missing}"


def test_gt_boundaries_within_duration(manifest, gt_records):
    for record in manifest:
        vid = record["id"]
        if vid not in gt_records:
            continue
        gt = gt_records[vid]
        dur = record["duration_sec"]
        for b in gt.get("boundaries_sec", []):
            assert 0 < b < dur, \
                f"{vid}: boundary {b}s out of range [0, {dur}]"


def test_gt_boundaries_sorted(gt_records):
    for vid, gt in gt_records.items():
        boundaries = gt.get("boundaries_sec", [])
        assert boundaries == sorted(boundaries), \
            f"{vid}: boundaries not sorted: {boundaries}"


def test_gt_chapter_count_matches_manifest(manifest, gt_records):
    for record in manifest:
        vid = record["id"]
        if vid not in gt_records:
            continue
        gt = gt_records[vid]
        n_boundaries = len(gt.get("boundaries_sec", []))
        n_chapters_gt = n_boundaries + 1
        n_chapters_manifest = record["num_chapters"]
        assert n_chapters_gt == n_chapters_manifest, \
            f"{vid}: GT has {n_chapters_gt} chapters but manifest says {n_chapters_manifest}"
