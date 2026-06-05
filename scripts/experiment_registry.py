"""Build a compact registry of final and diagnostic LECSEG experiments."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


OFFICIAL_BEST = {
    "name": "method_selector_extra_trainrank_balanced_k80",
    "pk": 0.3588,
    "wd": 0.3739,
    "boundary_similarity": 0.0757,
    "f1_tol2": 0.0893,
}


RESULT_SPECS = [
    {
        "artifact": "results/method_selector_experiment_trainrank_balanced_k50.json",
        "family": "selector",
        "status": "diagnostic",
    },
    {
        "artifact": "results/method_selector_experiment_trainrank_balanced_k60.json",
        "family": "selector",
        "status": "diagnostic",
    },
    {
        "artifact": "results/method_selector_experiment_trainrank_balanced_k70.json",
        "family": "selector",
        "status": "diagnostic",
    },
    {
        "artifact": "results/method_selector_experiment_trainrank_balanced_k90.json",
        "family": "selector",
        "status": "diagnostic",
    },
    {
        "artifact": "results/method_selector_experiment_trainrank_balanced_k100.json",
        "family": "selector",
        "status": "diagnostic",
    },
    {
        "artifact": "results/guarded_selector_balanced_k80_ridge.json",
        "family": "guarded_selector",
        "status": "rejected",
    },
    {
        "artifact": "results/direct_metric_search_seed11_s300.json",
        "family": "direct_metric_search",
        "status": "rejected",
    },
    {
        "artifact": "results/direct_metric_search_seed23_s300.json",
        "family": "direct_metric_search",
        "status": "rejected",
    },
    {
        "artifact": "results/eval_cross_model_tuning_focused_bge_e5large.json",
        "family": "cross_model_grid",
        "status": "rejected",
    },
    {
        "artifact": "results/eval_cross_model_tuning_focused_bge_e5.json",
        "family": "cross_model_grid",
        "status": "rejected",
    },
    {
        "artifact": "results/eval_cross_model_tuning_focused_e5large_bge.json",
        "family": "cross_model_grid",
        "status": "rejected",
    },
    {
        "artifact": "results/eval_treeseg_same_dataset_bge_large.json",
        "family": "treeseg_same_dataset",
        "status": "same_dataset_baseline",
    },
    {
        "artifact": "results/eval_treeseg_same_dataset_e5large.json",
        "family": "treeseg_same_dataset",
        "status": "same_dataset_baseline",
    },
    {
        "artifact": "results/eval_treeseg_same_dataset_mpnet.json",
        "family": "treeseg_same_dataset",
        "status": "same_dataset_baseline",
    },
]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_value(metrics: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = metrics.get(name)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _best_from_report(report: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    if "best_method" in report and isinstance(report["best_method"], dict):
        best = dict(report["best_method"])
        name = str(best.pop("name", "best_method"))
        return name, best

    rows: list[tuple[str, dict[str, Any]]] = []
    for section in ("methods", "summary", "selectors"):
        section_obj = report.get(section)
        if not isinstance(section_obj, dict):
            continue
        for name, metrics in section_obj.items():
            if not isinstance(metrics, dict):
                continue
            if "metrics" in metrics and isinstance(metrics["metrics"], dict):
                metrics = metrics["metrics"]
            if "pk" in metrics and "wd" in metrics:
                rows.append((name, metrics))
    if not rows:
        return None
    return min(rows, key=lambda row: (float(row[1]["pk"]), float(row[1]["wd"])))


def build_registry() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    entries.append(
        {
            "name": OFFICIAL_BEST["name"],
            "family": "official",
            "artifact": "results/method_selector_significance.json",
            "status": "official_best",
            "pk": OFFICIAL_BEST["pk"],
            "wd": OFFICIAL_BEST["wd"],
            "boundary_similarity": OFFICIAL_BEST["boundary_similarity"],
            "f1_tol2": OFFICIAL_BEST["f1_tol2"],
            "delta_pk_vs_official": 0.0,
            "delta_wd_vs_official": 0.0,
        }
    )

    for spec in RESULT_SPECS:
        path = ROOT / spec["artifact"]
        if not path.exists():
            continue
        report = _read_json(path)
        best = _best_from_report(report)
        if best is None:
            continue
        name, metrics = best
        pk = _metric_value(metrics, "pk")
        wd = _metric_value(metrics, "wd")
        if pk is None or wd is None:
            continue
        entries.append(
            {
                "name": name,
                "family": spec["family"],
                "artifact": spec["artifact"],
                "status": spec["status"],
                "pk": pk,
                "wd": wd,
                "boundary_similarity": _metric_value(metrics, "boundary_similarity", "bs"),
                "f1_tol2": _metric_value(metrics, "f1_tol2", "f1_t2", "f1"),
                "delta_pk_vs_official": pk - OFFICIAL_BEST["pk"],
                "delta_wd_vs_official": wd - OFFICIAL_BEST["wd"],
            }
        )

    ranked = sorted(entries, key=lambda row: (row["pk"], row["wd"]))
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "official_best": OFFICIAL_BEST,
        "entries": entries,
        "ranked_by_pk_wd": ranked,
    }


def write_markdown(registry: dict[str, Any], path: Path) -> None:
    lines = [
        "# Experiment Registry\n",
        "\n",
        f"Generated: {registry['generated_at']}\n",
        "\n",
        "This registry summarizes official and diagnostic experiments. A positive delta means worse than the official result.\n",
        "\n",
        "| Rank | Status | Family | Method | Pk | WD | F1@2 | dPk | dWD | Artifact |\n",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---|\n",
    ]
    for idx, row in enumerate(registry["ranked_by_pk_wd"], start=1):
        lines.append(
            "| {rank} | {status} | {family} | `{name}` | {pk:.4f} | {wd:.4f} | {f1} | {dpk:+.4f} | {dwd:+.4f} | `{artifact}` |\n".format(
                rank=idx,
                status=row["status"],
                family=row["family"],
                name=row["name"],
                pk=row["pk"],
                wd=row["wd"],
                f1="" if row.get("f1_tol2") is None else f"{row['f1_tol2']:.4f}",
                dpk=row["delta_pk_vs_official"],
                dwd=row["delta_wd_vs_official"],
                artifact=row["artifact"],
            )
        )
    path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    registry = build_registry()
    out_json = ROOT / "results" / "experiment_registry.json"
    out_md = ROOT / "docs" / "EXPERIMENT_REGISTRY.md"
    out_json.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    write_markdown(registry, out_md)
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


if __name__ == "__main__":
    main()
