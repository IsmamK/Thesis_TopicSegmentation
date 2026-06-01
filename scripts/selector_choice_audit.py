"""Per-video audit of balanced selector choices.

This complements the aggregate selector result by showing which held-out videos
benefit, which videos regress, and which method families the selector chooses.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from method_portfolio_analysis import DEFAULT_INPUTS, _extract_per_video  # noqa: E402
from selector_significance import _normalize_metric_keys  # noqa: E402


METRICS = ("pk", "wd", "boundary_similarity", "f1_tol2")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_manifest() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for line in (ROOT / "data" / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            rows[str(obj["id"])] = obj
    return rows


def _load_portfolio(input_paths: list[Path]) -> dict[str, dict[str, dict[str, float]]]:
    portfolio: dict[str, dict[str, dict[str, float]]] = {}
    for path in input_paths:
        if not path.exists():
            continue
        for method, by_video in _extract_per_video(path).items():
            name = method if method not in portfolio else f"{path.stem}::{method}"
            portfolio[name] = by_video
    return portfolio


def _method_family(method: str) -> str:
    if method.startswith("cross_rank"):
        return "cross-rank"
    if method.startswith("cross_e5"):
        return "cross-e5"
    if method.startswith("multi_res"):
        return "multi-resolution"
    if method.startswith("mm_"):
        return "multimodal-grid"
    if method.startswith("divisive"):
        return "divisive"
    if method.startswith("rank_") or "text" in method:
        return "ranker"
    return "other"


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _short_method(method: str, max_len: int = 44) -> str:
    return method if len(method) <= max_len else method[: max_len - 3] + "..."


def _latex_escape(text: str) -> str:
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
    )


def _mean(rows: list[dict[str, float]]) -> dict[str, float]:
    return {
        key: float(np.mean([row[key] for row in rows if key in row]))
        for key in METRICS
    }


def _selector_rows(
    manifest: dict[str, dict[str, Any]],
    portfolio: dict[str, dict[str, dict[str, float]]],
    selector: dict[str, Any],
    baseline_method: str,
    current_method: str,
    selector_name: str,
) -> list[dict[str, Any]]:
    choices = selector["selectors"][selector_name]["choices"]
    rows = []
    for video_id, chosen in sorted(choices.items()):
        base = _normalize_metric_keys(portfolio[baseline_method][video_id])
        current = _normalize_metric_keys(portfolio[current_method][video_id])
        selected = _normalize_metric_keys(portfolio[chosen][video_id])
        meta = manifest[video_id]
        rows.append(
            {
                "video_id": video_id,
                "domain": meta["domain"],
                "title": meta["title"],
                "chapters": int(meta["num_chapters"]),
                "chosen_method": chosen,
                "chosen_family": _method_family(chosen),
                "switched_from_current": chosen != current_method,
                "baseline": base,
                "current": current,
                "selector": selected,
                "delta_pk_vs_baseline": selected["pk"] - base["pk"],
                "delta_wd_vs_baseline": selected["wd"] - base["wd"],
                "delta_pk_vs_current": selected["pk"] - current["pk"],
                "delta_wd_vs_current": selected["wd"] - current["wd"],
                "delta_f1_vs_current": selected["f1_tol2"] - current["f1_tol2"],
            }
        )
    return rows


def build_report(
    input_paths: list[Path],
    selector_path: Path,
    selector_name: str,
    baseline_method: str,
    current_method: str,
) -> dict[str, Any]:
    manifest = _load_manifest()
    portfolio = _load_portfolio(input_paths)
    selector_abs = selector_path if selector_path.is_absolute() else ROOT / selector_path
    selector = _read_json(selector_abs)
    rows = _selector_rows(manifest, portfolio, selector, baseline_method, current_method, selector_name)

    family_counts = Counter(row["chosen_family"] for row in rows)
    method_counts = Counter(row["chosen_method"] for row in rows)
    switched = [row for row in rows if row["switched_from_current"]]
    improved_baseline_pk = [row for row in rows if row["delta_pk_vs_baseline"] < 0]
    improved_current_pk = [row for row in rows if row["delta_pk_vs_current"] < 0]
    improved_current_f1 = [row for row in rows if row["delta_f1_vs_current"] > 0]
    worst_vs_current = sorted(rows, key=lambda row: row["delta_pk_vs_current"], reverse=True)[:6]
    best_vs_current = sorted(rows, key=lambda row: row["delta_pk_vs_current"])[:6]

    return {
        "meta": {
            "selector_file": str(selector_abs.relative_to(ROOT)),
            "selector_name": selector_name,
            "baseline_method": baseline_method,
            "current_method": current_method,
            "n_videos": len(rows),
        },
        "summary": {
            "switch_count": len(switched),
            "improved_pk_vs_baseline": len(improved_baseline_pk),
            "improved_pk_vs_current": len(improved_current_pk),
            "improved_f1_vs_current": len(improved_current_f1),
            "family_counts": dict(sorted(family_counts.items())),
            "top_methods": dict(method_counts.most_common(10)),
            "selector_mean": _mean([row["selector"] for row in rows]),
            "current_mean": _mean([row["current"] for row in rows]),
            "baseline_mean": _mean([row["baseline"] for row in rows]),
        },
        "best_vs_current": best_vs_current,
        "worst_vs_current": worst_vs_current,
        "rows": rows,
    }


def _markdown_rows(rows: list[dict[str, Any]]) -> list[str]:
    out = [
        "| Video | Domain | Chosen family | Delta Pk vs cross | Selector Pk | Cross Pk | Delta F1@2 |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        out.append(
            "| {video} | {domain} | {family} | {dpk} | {spk} | {cpk} | {df1} |".format(
                video=row["video_id"],
                domain=row["domain"],
                family=row["chosen_family"],
                dpk=_fmt(row["delta_pk_vs_current"]),
                spk=_fmt(row["selector"]["pk"]),
                cpk=_fmt(row["current"]["pk"]),
                df1=_fmt(row["delta_f1_vs_current"]),
            )
        )
    return out


def _markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Selector Choice Audit",
        "",
        "Generated by `python scripts/selector_choice_audit.py`.",
        "",
        "## Summary",
        "",
        f"- Switches away from the cross-model method: {summary['switch_count']}/{report['meta']['n_videos']}.",
        f"- Improves Pk over BGE-divisive baseline: {summary['improved_pk_vs_baseline']}/{report['meta']['n_videos']}.",
        f"- Improves Pk over cross-model method: {summary['improved_pk_vs_current']}/{report['meta']['n_videos']}.",
        f"- Improves F1@2 over cross-model method: {summary['improved_f1_vs_current']}/{report['meta']['n_videos']}.",
        "",
        "Chosen method families:",
    ]
    for family, count in summary["family_counts"].items():
        lines.append(f"- {family}: {count}")
    lines.extend(["", "## Largest Pk Gains vs Cross-Model", ""])
    lines.extend(_markdown_rows(report["best_vs_current"]))
    lines.extend(["", "## Largest Pk Regressions vs Cross-Model", ""])
    lines.extend(_markdown_rows(report["worst_vs_current"]))
    lines.append("")
    return "\n".join(lines)


def _latex(report: dict[str, Any]) -> str:
    rows = report["best_vs_current"][:3] + report["worst_vs_current"][:3]
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\caption{Largest balanced-selector per-video Pk changes relative to the cross-model method.}",
        r"\label{tab:selector_choice_audit}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Video & Domain & $\Delta P_k$ & Sel. Pk & Cross Pk & $\Delta$F1@2 \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    _latex_escape(row["video_id"]),
                    _latex_escape(row["domain"].title() if row["domain"] != "CS" else "CS"),
                    _fmt(row["delta_pk_vs_current"]),
                    _fmt(row["selector"]["pk"]),
                    _fmt(row["current"]["pk"]),
                    _fmt(row["delta_f1_vs_current"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="*", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--selector", type=Path, default=ROOT / "results" / "method_selector_experiment_trainrank_balanced.json")
    parser.add_argument("--selector-name", default="extra")
    parser.add_argument("--baseline-method", default="divisive")
    parser.add_argument("--current-method", default="cross_e5_frac70_minlen11__align_contains_before")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "selector_choice_audit.json")
    parser.add_argument("--docs-output", type=Path, default=ROOT / "docs" / "SELECTOR_CHOICE_AUDIT.md")
    parser.add_argument("--tex-output", type=Path, default=ROOT / "thesis" / "tables" / "selector_choice_audit.tex")
    args = parser.parse_args()

    report = build_report(args.inputs, args.selector, args.selector_name, args.baseline_method, args.current_method)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.docs_output.parent.mkdir(parents=True, exist_ok=True)
    args.tex_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    args.docs_output.write_text(_markdown(report), encoding="utf-8")
    args.tex_output.write_text(_latex(report), encoding="utf-8")

    summary = report["summary"]
    print(f"Wrote {args.output}")
    print(f"Wrote {args.docs_output}")
    print(f"Wrote {args.tex_output}")
    print(
        "Switches={switch_count}/{n}; Pk wins vs current={pk_wins}; F1 wins vs current={f1_wins}".format(
            switch_count=summary["switch_count"],
            n=report["meta"]["n_videos"],
            pk_wins=summary["improved_pk_vs_current"],
            f1_wins=summary["improved_f1_vs_current"],
        )
    )


if __name__ == "__main__":
    main()
