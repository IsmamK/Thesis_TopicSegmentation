"""Generate a thesis claim ledger from current LECSEG result artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _claim(claim: str, evidence: str, status: str, wording: str) -> dict[str, str]:
    return {
        "claim": claim,
        "evidence": evidence,
        "status": status,
        "wording": wording,
    }


def build_claims() -> list[dict[str, str]]:
    sig = _read(ROOT / "results" / "method_selector_significance.json")
    domain = _read(ROOT / "results" / "domain_performance_analysis.json")
    robustness = _read(ROOT / "results" / "selector_robustness_analysis.json")
    choice = _read(ROOT / "results" / "selector_choice_audit.json")
    leave_domain = _read(ROOT / "results" / "selector_leave_domain_out.json")
    oracle = _read(ROOT / "results" / "method_portfolio_analysis.json")

    baseline = sig["summary"]["baseline"]
    current = sig["summary"]["current"]
    selector = sig["summary"]["selector"]
    current_vs_baseline = sig["current_vs_baseline"]["metrics"]
    selector_vs_baseline = sig["selector_vs_baseline"]["metrics"]
    selector_vs_current = sig["selector_vs_current"]["metrics"]

    domain_rows = domain["rows"]
    improved_domains = sum(1 for row in domain_rows if row["selector_delta_pk_vs_baseline"] < 0)
    failed_domains = [row["domain"].title() if row["domain"] != "CS" else "CS" for row in domain_rows if row["selector_delta_pk_vs_baseline"] > 0]
    leave = leave_domain["summary"]["leave_domain_out_selector"]
    oracle_metrics = oracle["per_video_oracle"]["metrics"]

    return [
        _claim(
            "LECSEG-30 is a compact lecture benchmark with hierarchical labels.",
            "data/manifest.jsonl, data/gt/, data/gt_hier/, data/gt_hier/iaa_report.json",
            "Supported",
            "30 public lectures, 32.52 hours, 419 creator chapter boundaries, 904 reviewed subtopics, chapter kappa 0.5351.",
        ),
        _claim(
            "Cross-model conservative selection significantly improves Pk/WD over BGE-divisive.",
            "results/method_selector_significance.json::current_vs_baseline",
            "Supported",
            "Pk improves from {bpk} to {cpk} (delta {dpk}, p={ppk}); WD improves from {bwd} to {cwd} (delta {dwd}, p={pwd}).".format(
                bpk=_fmt(baseline["pk"]),
                cpk=_fmt(current["pk"]),
                dpk=_fmt(current_vs_baseline["pk"]["delta"]),
                ppk=_fmt(current_vs_baseline["pk"]["p_value"]),
                bwd=_fmt(baseline["wd"]),
                cwd=_fmt(current["wd"]),
                dwd=_fmt(current_vs_baseline["wd"]["delta"]),
                pwd=_fmt(current_vs_baseline["wd"]["p_value"]),
            ),
        ),
        _claim(
            "Balanced method selection gives the best deployable mean Pk/WD operating point.",
            "results/method_selector_significance.json, results/selector_operating_point_analysis.json",
            "Supported with caveat",
            "Balanced selector reaches Pk={pk}, WD={wd}, BS={bs}, F1@2={f1}; its Pk/WD gains over cross-model are not significant.".format(
                pk=_fmt(selector["pk"]),
                wd=_fmt(selector["wd"]),
                bs=_fmt(selector["boundary_similarity"]),
                f1=_fmt(selector["f1_tol2"]),
            ),
        ),
        _claim(
            "Balanced selector significantly improves Pk/WD over BGE-divisive.",
            "results/method_selector_significance.json::selector_vs_baseline",
            "Supported",
            "Pk delta {dpk}, p={ppk}; WD delta {dwd}, p={pwd}.".format(
                dpk=_fmt(selector_vs_baseline["pk"]["delta"]),
                ppk=_fmt(selector_vs_baseline["pk"]["p_value"]),
                dwd=_fmt(selector_vs_baseline["wd"]["delta"]),
                pwd=_fmt(selector_vs_baseline["wd"]["p_value"]),
            ),
        ),
        _claim(
            "Balanced selector improves boundary-hit metrics over cross-model.",
            "results/method_selector_significance.json::selector_vs_current",
            "Supported",
            "BS delta {dbs}, p={pbs}; F1@2 delta {df1}, p={pf1}.".format(
                dbs=_fmt(selector_vs_current["boundary_similarity"]["delta"]),
                pbs=_fmt(selector_vs_current["boundary_similarity"]["p_value"]),
                df1=_fmt(selector_vs_current["f1_tol2"]["delta"]),
                pf1=_fmt(selector_vs_current["f1_tol2"]["p_value"]),
            ),
        ),
        _claim(
            "The selector result is sensitive to method-pool size.",
            "results/selector_robustness_analysis.json",
            "Supported",
            "Among tested balanced selector pools, k80 is best for Pk and WD; k120 worsens to Pk=0.3716, WD=0.3852.",
        ),
        _claim(
            "Selector gains are not uniform across academic domains.",
            "results/domain_performance_analysis.json",
            "Supported",
            "Selector improves Pk over BGE-divisive in {n}/5 domains; failure domains: {failures}.".format(
                n=improved_domains,
                failures=", ".join(failed_domains) if failed_domains else "none",
            ),
        ),
        _claim(
            "The selector is not domain-general under leave-one-domain-out evaluation.",
            "results/selector_leave_domain_out.json",
            "Supported negative result",
            "Leave-domain-out selector drops to Pk={pk}, WD={wd}, worse than BGE-divisive and cross-model.".format(
                pk=_fmt(leave["pk"]),
                wd=_fmt(leave["wd"]),
            ),
        ),
        _claim(
            "Candidate/method selection remains the main bottleneck.",
            "results/method_portfolio_analysis.json, results/selector_choice_audit.json",
            "Supported diagnostic",
            "Per-video oracle reaches Pk={pk}, WD={wd}; balanced selector switches on 30/30 videos but improves Pk over cross-model on only 9/30.".format(
                pk=_fmt(oracle_metrics["pk"]),
                wd=_fmt(oracle_metrics["wd"]),
            ),
        ),
        _claim(
            "LECSEG should not be presented as universal external best system.",
            "docs/RELATED_WORK_COMPARISON.md, results/selector_leave_domain_out.json",
            "Required caveat",
            "Large supervised chaptering systems use far more data; LECSEG's contribution is a reproducible low-resource lecture benchmark and analysis artifact.",
        ),
    ]


def _markdown(claims: list[dict[str, str]]) -> str:
    lines = [
        "# Defensible Claims Ledger",
        "",
        "Generated by `python scripts/generate_defensible_claims.py`.",
        "",
        "| Claim | Status | Evidence | Safe wording |",
        "| --- | --- | --- | --- |",
    ]
    for claim in claims:
        lines.append(
            "| {claim} | {status} | `{evidence}` | {wording} |".format(
                claim=claim["claim"],
                status=claim["status"],
                evidence=claim["evidence"],
                wording=claim["wording"],
            )
        )
    lines.extend(
        [
            "",
            "## Non-Claims",
            "",
            "- Do not claim universal external best-system performance.",
            "- Do not claim sub-0.30 deployable Pk/WD.",
            "- Do not claim the selector is domain-general.",
            "- Do not claim every modality improves segmentation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "DEFENSIBLE_CLAIMS.md")
    parser.add_argument("--json-output", type=Path, default=ROOT / "results" / "defensible_claims.json")
    args = parser.parse_args()

    claims = build_claims()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_markdown(claims), encoding="utf-8")
    args.json_output.write_text(json.dumps({"claims": claims}, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.json_output}")
    print(f"Claims: {len(claims)}")


if __name__ == "__main__":
    main()
