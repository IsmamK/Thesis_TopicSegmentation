"""Validate thesis-facing LECSEG claims against authoritative local artifacts.

This script is intentionally conservative: it checks only facts that are used
in the thesis/paper narrative and should remain stable unless the benchmark or
official result policy changes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DATASET = {
    "videos": 30,
    "duration_sec": 117_083,
    "duration_hours": 32.52,
    "chapter_boundaries": 419,
    "reviewed_hier_files": 30,
    "subtopics": 904,
}

EXPECTED_DOMAINS = {
    "BIOLOGY": {"videos": 6, "duration_sec": 16_999, "chapters": 94},
    "CS": {"videos": 7, "duration_sec": 40_871, "chapters": 98},
    "MATH": {"videos": 4, "duration_sec": 12_704, "chapters": 55},
    "PHILOSOPHY": {"videos": 6, "duration_sec": 20_277, "chapters": 122},
    "PHYSICS": {"videos": 7, "duration_sec": 26_232, "chapters": 50},
}

EXPECTED_IAA = {
    "n_videos": 30,
    "mean_kappa_chapter": 0.5351,
    "mean_kappa_subtopic": 0.4257,
    "mean_f1_chapter": 1.0,
    "mean_f1_subtopic": 0.7793,
}

EXPECTED_SUMMARY = {
    "baseline": {
        "pk": 0.3884,
        "wd": 0.3956,
        "boundary_similarity": 0.1292,
        "f1_tol2": 0.0878,
    },
    "current": {
        "pk": 0.3713,
        "wd": 0.3764,
        "boundary_similarity": 0.0362,
        "f1_tol2": 0.0237,
    },
    "selector": {
        "pk": 0.3588,
        "wd": 0.3739,
        "boundary_similarity": 0.0757,
        "f1_tol2": 0.0893,
    },
}

EXPECTED_SIGNIFICANCE = {
    ("current_vs_baseline", "pk"): {"delta": -0.0171, "p_value": 0.0064, "significant": True},
    ("current_vs_baseline", "wd"): {"delta": -0.0193, "p_value": 0.0001, "significant": True},
    ("selector_vs_current", "pk"): {"delta": -0.0126, "p_value": 0.3560, "significant": False},
    ("selector_vs_current", "wd"): {"delta": -0.0025, "p_value": 0.9039, "significant": False},
    ("selector_vs_current", "boundary_similarity"): {"delta": 0.0395, "p_value": 0.0076, "significant": True},
    ("selector_vs_current", "f1_tol2"): {"delta": 0.0656, "p_value": 0.0076, "significant": True},
}

EXPECTED_TABLE_STRINGS = [
    "BGE-divisive baseline | 0.3884 | 0.3956 | 0.1292 | 0.0878",
    "Cross-model conservative | 0.3713 | 0.3764 | 0.0362 | 0.0237",
    "LOO ExtraTrees method selector | 0.3588 | 0.3739 | 0.0757 | 0.0893",
    "Per-video method oracle | 0.2980 | 0.3280 | 0.1366 | 0.1676",
    "MiniSeg/YTSEG | 19,299 | 6,533 h",
    "VidChapters-7M | 817,000 | 7M chapters",
]

EXPECTED_OPERATING_POINT_STRINGS = [
    "Balanced selector | 0.3588 | 0.3739 | 0.0757 | 0.0893",
    "Text-transition ranker | 0.3937 | 0.4154 | 0.1163 | 0.1701",
    "Best deployable Pk/WD operating point: Balanced selector.",
]

RISKY_PATTERNS = [
    r"\b55\s+hours\b",
    r"\b329\s+chapters\b",
    r"\bstate-of-the-art\b",
    r"\bfirst\s+open\b",
    r"\boutperforms\s+all\b",
    r"\bsub-0\.30\b",
    r"huggingface\.co/",
    r"zenodo\.org/",
    r"0\.0169",
    r"\\todo\{",
]

SCAN_GLOBS = [
    "thesis/**/*.tex",
    "paper/**/*.tex",
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _approx(actual: float, expected: float, places: int = 4) -> bool:
    return round(float(actual), places) == round(float(expected), places)


def _record(checks: list[dict[str, Any]], name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def _dataset_checks(checks: list[dict[str, Any]]) -> None:
    manifest = _read_manifest(ROOT / "data" / "manifest.jsonl")
    gt_files = [p for p in (ROOT / "data" / "gt").glob("*.json") if p.name != ".gitkeep"]
    hier_files = [p for p in (ROOT / "data" / "gt_hier").glob("*.json") if p.name not in {".gitkeep", "iaa_report.json"}]

    chapters_by_video = {p.stem: int(_read_json(p)["num_chapters"]) for p in gt_files}
    hier_by_video = {p.stem: _read_json(p) for p in hier_files}

    facts = {
        "videos": len(manifest),
        "duration_sec": sum(int(row["duration_sec"]) for row in manifest),
        "duration_hours": round(sum(int(row["duration_sec"]) for row in manifest) / 3600, 2),
        "chapter_boundaries": sum(chapters_by_video.values()),
        "reviewed_hier_files": sum(1 for row in hier_by_video.values() if row.get("status") == "reviewed"),
        "subtopics": sum(len(row.get("subtopics", [])) for row in hier_by_video.values()),
    }

    for key, expected in EXPECTED_DATASET.items():
        actual = facts[key]
        ok = _approx(actual, expected, 2) if isinstance(expected, float) else actual == expected
        _record(checks, f"dataset:{key}", ok, f"actual={actual}, expected={expected}")

    domain_counts: dict[str, dict[str, int]] = {}
    for row in manifest:
        domain = str(row["domain"]).upper()
        domain_counts.setdefault(domain, {"videos": 0, "duration_sec": 0, "chapters": 0})
        domain_counts[domain]["videos"] += 1
        domain_counts[domain]["duration_sec"] += int(row["duration_sec"])
        domain_counts[domain]["chapters"] += chapters_by_video.get(str(row["id"]), 0)

    _record(
        checks,
        "dataset:domains",
        domain_counts == EXPECTED_DOMAINS,
        f"actual={domain_counts}, expected={EXPECTED_DOMAINS}",
    )


def _iaa_checks(checks: list[dict[str, Any]]) -> None:
    report = _read_json(ROOT / "data" / "gt_hier" / "iaa_report.json")
    aggregate = report["aggregate"]
    for key, expected in EXPECTED_IAA.items():
        actual = aggregate[key]
        ok = _approx(actual, expected, 4) if isinstance(expected, float) else actual == expected
        _record(checks, f"iaa:{key}", ok, f"actual={actual}, expected={expected}")


def _result_checks(checks: list[dict[str, Any]]) -> None:
    report = _read_json(ROOT / "results" / "method_selector_significance.json")
    for method, metrics in EXPECTED_SUMMARY.items():
        for metric, expected in metrics.items():
            actual = report["summary"][method][metric]
            _record(
                checks,
                f"summary:{method}:{metric}",
                _approx(actual, expected, 4),
                f"actual={actual:.4f}, expected={expected:.4f}",
            )

    for (comparison, metric), expected_values in EXPECTED_SIGNIFICANCE.items():
        actual_row = report[comparison]["metrics"][metric]
        for key, expected in expected_values.items():
            actual = actual_row[key]
            ok = actual == expected if isinstance(expected, bool) else _approx(actual, expected, 4)
            _record(
                checks,
                f"significance:{comparison}:{metric}:{key}",
                ok,
                f"actual={actual}, expected={expected}",
            )


def _table_checks(checks: list[dict[str, Any]]) -> None:
    table_doc = (ROOT / "docs" / "THESIS_RESULT_TABLES.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_TABLE_STRINGS:
        _record(
            checks,
            f"tables:contains:{expected[:35]}",
            expected in table_doc,
            f"expected snippet={expected!r}",
        )

    for name in ("main_results.tex", "significance.tex", "external_scale.tex"):
        path = ROOT / "thesis" / "tables" / name
        _record(checks, f"tables:file:{name}", path.exists() and path.stat().st_size > 0, str(path))

    operating_doc = (ROOT / "docs" / "SELECTOR_OPERATING_POINTS.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_OPERATING_POINT_STRINGS:
        _record(
            checks,
            f"selector-operating:contains:{expected[:35]}",
            expected in operating_doc,
            f"expected snippet={expected!r}",
        )
    op_table = ROOT / "thesis" / "tables" / "selector_operating_points.tex"
    _record(
        checks,
        "tables:file:selector_operating_points.tex",
        op_table.exists() and op_table.stat().st_size > 0,
        str(op_table),
    )


def _scan_claims(checks: list[dict[str, Any]]) -> None:
    paths: list[Path] = []
    for glob in SCAN_GLOBS:
        paths.extend(ROOT.glob(glob))
    paths = sorted(set(paths))

    hits: dict[str, list[str]] = {}
    compiled = [(pattern, re.compile(pattern, flags=re.IGNORECASE)) for pattern in RISKY_PATTERNS]
    for path in paths:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for pattern, regex in compiled:
            for match in regex.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                hits.setdefault(pattern, []).append(f"{path.relative_to(ROOT)}:{line_no}")

    _record(
        checks,
        "claims:risky-patterns",
        not hits,
        "no risky patterns found" if not hits else json.dumps(hits, indent=2),
    )


def _consistency_checks(checks: list[dict[str, Any]]) -> None:
    project_guide = (ROOT / "docs" / "PROJECT_GUIDE.md").read_text(encoding="utf-8-sig")
    required = [
        "32.52 hours",
        "Chapter boundaries | 419",
        "cross_e5_frac70_minlen11__align_contains_before",
        "ExtraTrees method selector",
        "not statistically significant",
    ]
    for snippet in required:
        _record(
            checks,
            f"guide:contains:{snippet[:35]}",
            snippet in project_guide,
            f"expected snippet={snippet!r}",
        )


def run() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    _dataset_checks(checks)
    _iaa_checks(checks)
    _result_checks(checks)
    _table_checks(checks)
    _scan_claims(checks)
    _consistency_checks(checks)
    passed = sum(1 for check in checks if check["ok"])
    failed = len(checks) - passed
    return {
        "status": "pass" if failed == 0 else "fail",
        "passed": passed,
        "failed": failed,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    report = run()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"claim validation: {report['status']} ({report['passed']} passed, {report['failed']} failed)")
        for check in report["checks"]:
            if not check["ok"]:
                print(f"FAIL {check['name']}: {check['detail']}")

    if report["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
