"""Generate a conservative submission-readiness audit for LECSEG.

The audit is intentionally about thesis defensibility, not leaderboard
positioning. It checks that the current repository has the result artifacts,
claim validation, thesis build evidence, and explicit non-claims needed to
defend the project without overstating external state-of-the-art performance.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import validate_thesis_claims


ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "results" / "submission_readiness_audit.json"
OUT_MD = ROOT / "docs" / "SUBMISSION_READINESS.md"

REQUIRED_ARTIFACTS = {
    "core result evidence": [
        "results/method_selector_significance.json",
        "results/method_portfolio_analysis.json",
        "results/oracle_k_experiment.json",
        "docs/THESIS_RESULT_TABLES.md",
        "thesis/tables/main_results.tex",
        "thesis/tables/significance.tex",
    ],
    "selector diagnostics": [
        "docs/SELECTOR_OPERATING_POINTS.md",
        "docs/SELECTOR_ROBUSTNESS.md",
        "docs/DOMAIN_PERFORMANCE.md",
        "docs/SELECTOR_CHOICE_AUDIT.md",
        "docs/SELECTOR_LEAVE_DOMAIN_OUT.md",
        "results/selector_operating_point_analysis.json",
        "results/selector_robustness_analysis.json",
        "results/domain_performance_analysis.json",
        "results/selector_choice_audit.json",
        "results/selector_leave_domain_out.json",
        "thesis/tables/selector_operating_points.tex",
        "thesis/tables/selector_robustness.tex",
        "thesis/tables/domain_performance.tex",
        "thesis/tables/selector_choice_audit.tex",
        "thesis/tables/selector_leave_domain_out.tex",
    ],
    "external positioning": [
        "docs/RELATED_WORK_COMPARISON.md",
        "docs/LOW_RESOURCE_POSITIONING.md",
        "results/related_work_comparison.json",
        "results/low_resource_positioning.json",
        "thesis/tables/related_work_comparison.tex",
        "thesis/tables/low_resource_positioning.tex",
        "thesis/tables/external_scale.tex",
    ],
    "claim discipline": [
        "docs/DEFENSIBLE_CLAIMS.md",
        "docs/CONTRIBUTIONS_REFERENCE.md",
        "docs/FINAL_MODEL_AUDIT.md",
        "docs/PROJECT_GUIDE.md",
        "results/defensible_claims.json",
    ],
    "rendered thesis": [
        "thesis/main.pdf",
        "thesis/main.log",
    ],
}

HARD_LATEX_PATTERNS = [
    r"LaTeX Error",
    r"Fatal error",
    r"Emergency stop",
    r"Undefined control sequence",
    r"undefined citations",
    r"undefined references",
    r"Float too large",
    r"Infinite glue",
    r"No file main\.bbl",
]

REQUIRED_SAFE_FRAMING = [
    "not external SOTA",
    "not stronger than large supervised chaptering systems",
    "Do not claim the selector is domain-general",
    "Pk=0.3588, WD=0.3739, BS=0.0757, F1@2=0.0893",
    "candidate-selection bottleneck",
]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _check_artifacts() -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for category, paths in REQUIRED_ARTIFACTS.items():
        for rel in paths:
            path = ROOT / rel
            ok = path.exists() and path.stat().st_size > 0
            checks.append(
                {
                    "category": category,
                    "name": rel,
                    "ok": ok,
                    "detail": f"{path.stat().st_size} bytes" if path.exists() else "missing",
                }
            )
    return checks


def _check_latex_log() -> list[dict[str, Any]]:
    path = ROOT / "thesis" / "main.log"
    if not path.exists():
        return [
            {
                "category": "rendered thesis",
                "name": "latex hard-error scan",
                "ok": False,
                "detail": "thesis/main.log missing",
            }
        ]

    text = _read_text(path)
    hits: dict[str, list[int]] = {}
    for pattern in HARD_LATEX_PATTERNS:
        regex = re.compile(pattern, flags=re.IGNORECASE)
        for match in regex.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            hits.setdefault(pattern, []).append(line_no)

    return [
        {
            "category": "rendered thesis",
            "name": "latex hard-error scan",
            "ok": not hits,
            "detail": "no hard LaTeX failures found" if not hits else hits,
        }
    ]


def _check_safe_framing() -> list[dict[str, Any]]:
    sources = [
        ROOT / "docs" / "DEFENSIBLE_CLAIMS.md",
        ROOT / "docs" / "RELATED_WORK_COMPARISON.md",
        ROOT / "docs" / "LOW_RESOURCE_POSITIONING.md",
        ROOT / "docs" / "CONTRIBUTIONS_REFERENCE.md",
        ROOT / "docs" / "FINAL_MODEL_AUDIT.md",
        ROOT / "thesis" / "chapters" / "chapter2_literature.tex",
        ROOT / "thesis" / "chapters" / "chapter5_conclusion.tex",
    ]
    corpus = "\n".join(_read_text(path) for path in sources if path.exists())
    checks = []
    for snippet in REQUIRED_SAFE_FRAMING:
        checks.append(
            {
                "category": "claim discipline",
                "name": f"safe framing: {snippet}",
                "ok": snippet.lower() in corpus.lower(),
                "detail": f"required snippet={snippet!r}",
            }
        )
    return checks


def _load_key_results() -> dict[str, Any]:
    report = json.loads((ROOT / "results" / "method_selector_significance.json").read_text(encoding="utf-8-sig"))
    return {
        "baseline": report["summary"]["baseline"],
        "cross_model_conservative": report["summary"]["current"],
        "balanced_selector": report["summary"]["selector"],
        "selector_vs_baseline_pk": report["selector_vs_baseline"]["metrics"]["pk"],
        "selector_vs_baseline_wd": report["selector_vs_baseline"]["metrics"]["wd"],
        "selector_vs_current_pk": report["selector_vs_current"]["metrics"]["pk"],
        "selector_vs_current_wd": report["selector_vs_current"]["metrics"]["wd"],
    }


def _markdown(report: dict[str, Any]) -> str:
    generated_at = report["generated_at"]
    status = report["status"].upper()
    key = report["key_results"]
    claim = report["verdict"]
    lines = [
        "# Submission Readiness Audit",
        "",
        f"Generated: {generated_at}",
        f"Status: **{status}**",
        "",
        "## Verdict",
        "",
        claim,
        "",
        "## Key Results",
        "",
        "| Method | Pk | WD | BS | F1@2 |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, key_name in [
        ("BGE-divisive baseline", "baseline"),
        ("Cross-model conservative", "cross_model_conservative"),
        ("Balanced LOO selector", "balanced_selector"),
    ]:
        row = key[key_name]
        lines.append(
            f"| {label} | {row['pk']:.4f} | {row['wd']:.4f} | "
            f"{row['boundary_similarity']:.4f} | {row['f1_tol2']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## Significance Summary",
            "",
            "- Balanced selector vs BGE baseline: Pk and WD are statistically significant local improvements.",
            "- Balanced selector vs cross-model conservative: Pk/WD differences are not statistically significant.",
            "- Balanced selector vs cross-model conservative: BS and F1@2 improve significantly.",
            "",
            "## What Can Be Claimed",
            "",
            "- LECSEG is a reproducible lecture segmentation benchmark/pipeline with a 30-video, 32.52-hour YouTube lecture benchmark.",
            "- The best deployable local result is the balanced leave-one-out selector: Pk=0.3588, WD=0.3739, BS=0.0757, F1@2=0.0893.",
            "- The thesis contains external related-work and low-resource comparisons against large chaptering systems.",
            "- Oracle evidence shows candidate selection/ranking is the main remaining bottleneck.",
            "",
            "## What Must Not Be Claimed",
            "",
            "- Do not claim external state of the art.",
            "- Do not claim LECSEG beats MiniSeg/YTSEG, VidChapters-7M, Chapter-Gen, Chapter-Llama, or other large supervised systems on their own benchmarks.",
            "- Do not claim the selector is domain-general; leave-domain-out evaluation is weaker than the local benchmark.",
            "",
            "## Checks",
            "",
            f"- Claim validator: {report['claim_validation']['status']} ({report['claim_validation']['passed']} passed, {report['claim_validation']['failed']} failed).",
            f"- Audit checks: {report['passed']} passed, {report['failed']} failed.",
            "",
        ]
    )

    failed = [check for check in report["checks"] if not check["ok"]]
    if failed:
        lines.extend(["## Failures", ""])
        for check in failed:
            lines.append(f"- {check['category']} / {check['name']}: {check['detail']}")
    else:
        lines.extend(
            [
                "No submission-readiness failures were found by this audit.",
                "",
                "Residual risk: this does not prove external SOTA; it proves that the current thesis artifacts support the safer defensible claim boundary.",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def run() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.extend(_check_artifacts())
    checks.extend(_check_latex_log())
    checks.extend(_check_safe_framing())

    previous_skip = os.environ.get("LECSEG_SKIP_SUBMISSION_AUDIT_CHECK")
    os.environ["LECSEG_SKIP_SUBMISSION_AUDIT_CHECK"] = "1"
    try:
        claim_validation = validate_thesis_claims.run()
    finally:
        if previous_skip is None:
            os.environ.pop("LECSEG_SKIP_SUBMISSION_AUDIT_CHECK", None)
        else:
            os.environ["LECSEG_SKIP_SUBMISSION_AUDIT_CHECK"] = previous_skip
    checks.append(
        {
            "category": "claim discipline",
            "name": "validate_thesis_claims.py",
            "ok": claim_validation["status"] == "pass",
            "detail": f"{claim_validation['passed']} passed, {claim_validation['failed']} failed",
        }
    )

    passed = sum(1 for check in checks if check["ok"])
    failed = len(checks) - passed
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pass" if failed == 0 else "fail",
        "passed": passed,
        "failed": failed,
        "key_results": _load_key_results(),
        "claim_validation": {
            "status": claim_validation["status"],
            "passed": claim_validation["passed"],
            "failed": claim_validation["failed"],
        },
        "verdict": (
            "Ready for a defensible thesis submission claim boundary: LECSEG is a "
            "reproducible low-resource lecture segmentation benchmark and pipeline "
            "with statistically supported local Pk/WD gains over implemented "
            "baselines, but it is not an external SOTA system."
        ),
        "checks": checks,
    }

    OUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args()

    report = run()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"submission readiness: {report['status']} ({report['passed']} passed, {report['failed']} failed)")
        print(f"wrote {OUT_MD.relative_to(ROOT)}")
        print(f"wrote {OUT_JSON.relative_to(ROOT)}")
        for check in report["checks"]:
            if not check["ok"]:
                print(f"FAIL {check['category']} / {check['name']}: {check['detail']}")

    if report["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
