"""Validate thesis-facing LECSEG claims against authoritative local artifacts.

This script is intentionally conservative: it checks only facts that are used
in the thesis/paper narrative and should remain stable unless the benchmark or
official result policy changes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
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

EXPECTED_SELECTOR_ROBUSTNESS_STRINGS = [
    "k30 | 30 | 0.3729 | 0.3780 | 0.0317 | 0.0226",
    "k50 | 50 | 0.3634 | 0.3760 | 0.0495 | 0.0608",
    "k80 | 80 | 0.3588 | 0.3739 | 0.0757 | 0.0893",
    "k120 | 120 | 0.3716 | 0.3852 | 0.0774 | 0.0929",
    "Best balanced Pk/WD setting: k80.",
]

EXPECTED_DOMAIN_PERFORMANCE_STRINGS = [
    "BIOLOGY | 6 | 94 | 0.4218 | 0.3968 | 0.3976",
    "CS | 7 | 98 | 0.3409 | 0.3295 | 0.3314",
    "MATH | 4 | 55 | 0.3724 | 0.3792 | 0.4014",
    "PHILOSOPHY | 6 | 122 | 0.4415 | 0.3948 | 0.3753",
    "PHYSICS | 7 | 50 | 0.3710 | 0.3667 | 0.3144",
    "Selector improves Pk over baseline in 4/5 domains.",
]

EXPECTED_SELECTOR_CHOICE_STRINGS = [
    "Switches away from the cross-model method: 30/30.",
    "Improves Pk over BGE-divisive baseline: 19/30.",
    "Improves Pk over cross-model method: 9/30.",
    "cross-e5: 14",
    "multimodal-grid: 12",
    "Hy7ou5R_vjE | PHYSICS | multimodal-grid | -0.1542",
    "j0wJBEZdwLs | MATH | multimodal-grid | 0.0754",
]

EXPECTED_LEAVE_DOMAIN_OUT_STRINGS = [
    "Leave-domain-out selector | 0.4012 | 0.4103 | 0.0465 | 0.0498",
    "BIOLOGY | 6 | 0.3986 | 0.4026 | 0.0462 | 0.0347",
    "PHYSICS | 7 | 0.4566 | 0.4652 | 0.0354 | 0.0519",
]

EXPECTED_DEFENSIBLE_CLAIMS_STRINGS = [
    "Cross-model conservative selection significantly improves Pk/WD over BGE-divisive.",
    "Balanced selector reaches Pk=0.3588, WD=0.3739, BS=0.0757, F1@2=0.0893",
    "Leave-domain-out selector drops to Pk=0.4012, WD=0.4103",
    "Per-video oracle reaches Pk=0.2980, WD=0.3280",
    "Do not claim the selector is domain-general.",
]

EXPECTED_RELATED_WORK_STRINGS = [
    "LECSEG-30 balanced selector (ours) | 30",
    "Pk=0.3588, WD=0.3739, BS=0.0757, F1@2=0.0893",
    "MiniSeg / YTSEG](https://arxiv.org/abs/2402.17633) | 19,299",
    "YTSEG MiniSeg: P=45.44, R=41.48, F1=43.37, Pk=28.73, BS=35.74.",
    "Chapter-Gen / multimodal video chapter generation](https://arxiv.org/abs/2209.12694) | 9,631",
    "VidChapters-7M](https://antoyang.github.io/vidchapters.html) | 817,000",
    "Chapter-Llama](https://openaccess.thecvf.com/content/CVPR2025/papers/Ventura_Chapter-Llama_Efficient_Chaptering_in_Hour-Long_Videos_with_LLMs_CVPR_2025_paper.pdf) | 10,000 train / 8,100 test",
    "TreeSeg / TinyRec](https://arxiv.org/abs/2407.12028) | 21",
    "AVLectures](https://arxiv.org/abs/2210.16644) | 2,350+",
    "Large supervised chaptering systems remain stronger on scale and reported external benchmark performance.",
]

EXPECTED_LOW_RESOURCE_STRINGS = [
    "Chapter-Gen / multimodal video chapter generation | 9,631 | 321.0x",
    "MiniSeg / YTSEG | 19,299 | 643.3x",
    "AVLectures | 2,350 | 78.3x",
    "VidChapters-7M | 817,000 | 27,233.3x",
    "LECSEG is not stronger than large supervised chaptering systems on external",
    "exposes the candidate-selection bottleneck at a tiny fraction of the scale.",
]

EXPECTED_SUBMISSION_READINESS_STRINGS = [
    "Ready for a defensible thesis submission claim boundary",
    "Balanced LOO selector | 0.3588 | 0.3739 | 0.0757 | 0.0893",
    "Do not claim external state of the art.",
    "Do not claim the selector is domain-general",
    "Residual risk: this does not prove external SOTA",
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

    robustness_doc = (ROOT / "docs" / "SELECTOR_ROBUSTNESS.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_SELECTOR_ROBUSTNESS_STRINGS:
        _record(
            checks,
            f"selector-robustness:contains:{expected[:35]}",
            expected in robustness_doc,
            f"expected snippet={expected!r}",
        )
    robustness_table = ROOT / "thesis" / "tables" / "selector_robustness.tex"
    _record(
        checks,
        "tables:file:selector_robustness.tex",
        robustness_table.exists() and robustness_table.stat().st_size > 0,
        str(robustness_table),
    )

    domain_doc = (ROOT / "docs" / "DOMAIN_PERFORMANCE.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_DOMAIN_PERFORMANCE_STRINGS:
        _record(
            checks,
            f"domain-performance:contains:{expected[:35]}",
            expected in domain_doc,
            f"expected snippet={expected!r}",
        )
    domain_table = ROOT / "thesis" / "tables" / "domain_performance.tex"
    _record(
        checks,
        "tables:file:domain_performance.tex",
        domain_table.exists() and domain_table.stat().st_size > 0,
        str(domain_table),
    )

    choice_doc = (ROOT / "docs" / "SELECTOR_CHOICE_AUDIT.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_SELECTOR_CHOICE_STRINGS:
        _record(
            checks,
            f"selector-choice:contains:{expected[:35]}",
            expected in choice_doc,
            f"expected snippet={expected!r}",
        )
    choice_table = ROOT / "thesis" / "tables" / "selector_choice_audit.tex"
    _record(
        checks,
        "tables:file:selector_choice_audit.tex",
        choice_table.exists() and choice_table.stat().st_size > 0,
        str(choice_table),
    )

    leave_domain_doc = (ROOT / "docs" / "SELECTOR_LEAVE_DOMAIN_OUT.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_LEAVE_DOMAIN_OUT_STRINGS:
        _record(
            checks,
            f"leave-domain-out:contains:{expected[:35]}",
            expected in leave_domain_doc,
            f"expected snippet={expected!r}",
        )
    leave_domain_table = ROOT / "thesis" / "tables" / "selector_leave_domain_out.tex"
    _record(
        checks,
        "tables:file:selector_leave_domain_out.tex",
        leave_domain_table.exists() and leave_domain_table.stat().st_size > 0,
        str(leave_domain_table),
    )

    claims_doc = (ROOT / "docs" / "DEFENSIBLE_CLAIMS.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_DEFENSIBLE_CLAIMS_STRINGS:
        _record(
            checks,
            f"defensible-claims:contains:{expected[:35]}",
            expected in claims_doc,
            f"expected snippet={expected!r}",
        )
    claims_json = ROOT / "results" / "defensible_claims.json"
    _record(
        checks,
        "results:file:defensible_claims.json",
        claims_json.exists() and claims_json.stat().st_size > 0,
        str(claims_json),
    )

    related_doc = (ROOT / "docs" / "RELATED_WORK_COMPARISON.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_RELATED_WORK_STRINGS:
        _record(
            checks,
            f"related-work:contains:{expected[:35]}",
            expected in related_doc,
            f"expected snippet={expected!r}",
        )
    related_json = ROOT / "results" / "related_work_comparison.json"
    _record(
        checks,
        "results:file:related_work_comparison.json",
        related_json.exists() and related_json.stat().st_size > 0,
        str(related_json),
    )
    related_table = ROOT / "thesis" / "tables" / "related_work_comparison.tex"
    _record(
        checks,
        "tables:file:related_work_comparison.tex",
        related_table.exists() and related_table.stat().st_size > 0,
        str(related_table),
    )

    low_resource_doc = (ROOT / "docs" / "LOW_RESOURCE_POSITIONING.md").read_text(encoding="utf-8-sig")
    for expected in EXPECTED_LOW_RESOURCE_STRINGS:
        _record(
            checks,
            f"low-resource:contains:{expected[:35]}",
            expected in low_resource_doc,
            f"expected snippet={expected!r}",
        )
    low_resource_json = ROOT / "results" / "low_resource_positioning.json"
    _record(
        checks,
        "results:file:low_resource_positioning.json",
        low_resource_json.exists() and low_resource_json.stat().st_size > 0,
        str(low_resource_json),
    )
    low_resource_table = ROOT / "thesis" / "tables" / "low_resource_positioning.tex"
    _record(
        checks,
        "tables:file:low_resource_positioning.tex",
        low_resource_table.exists() and low_resource_table.stat().st_size > 0,
        str(low_resource_table),
    )

    if os.environ.get("LECSEG_SKIP_SUBMISSION_AUDIT_CHECK") != "1":
        submission_doc = ROOT / "docs" / "SUBMISSION_READINESS.md"
        if submission_doc.exists():
            submission_text = submission_doc.read_text(encoding="utf-8-sig")
            for expected in EXPECTED_SUBMISSION_READINESS_STRINGS:
                _record(
                    checks,
                    f"submission-readiness:contains:{expected[:35]}",
                    expected in submission_text,
                    f"expected snippet={expected!r}",
                )
        else:
            _record(
                checks,
                "submission-readiness:file:SUBMISSION_READINESS.md",
                False,
                str(submission_doc),
            )
        submission_json = ROOT / "results" / "submission_readiness_audit.json"
        _record(
            checks,
            "results:file:submission_readiness_audit.json",
            submission_json.exists() and submission_json.stat().st_size > 0,
            str(submission_json),
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
        "scripts/submission_readiness_audit.py",
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
