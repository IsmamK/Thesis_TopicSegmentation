"""Compare one or more result JSON files against the official LECSEG best."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

OFFICIAL_PK = 0.3588
OFFICIAL_WD = 0.3739


def _best(report: dict[str, Any]) -> tuple[str, dict[str, float]] | None:
    if isinstance(report.get("best_method"), dict):
        best = dict(report["best_method"])
        name = str(best.pop("name", "best_method"))
        return name, best
    rows = []
    for key in ("methods", "summary", "selectors"):
        obj = report.get(key)
        if not isinstance(obj, dict):
            continue
        for name, metrics in obj.items():
            if isinstance(metrics, dict) and "metrics" in metrics:
                metrics = metrics["metrics"]
            if isinstance(metrics, dict) and "pk" in metrics and "wd" in metrics:
                rows.append((name, metrics))
    return min(rows, key=lambda row: (row[1]["pk"], row[1]["wd"])) if rows else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Result JSON files to compare. Defaults to results/eval*.json.",
    )
    args = parser.parse_args()
    paths = args.paths or sorted(Path("results").glob("eval*.json"))
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        best = _best(report)
        if best is None:
            print(f"{path}: no comparable method found")
            continue
        name, metrics = best
        pk = float(metrics["pk"])
        wd = float(metrics["wd"])
        verdict = "BEATS_OFFICIAL" if (pk, wd) < (OFFICIAL_PK, OFFICIAL_WD) else "does_not_beat"
        print(
            f"{path}: {name} Pk={pk:.4f} WD={wd:.4f} "
            f"dPk={pk - OFFICIAL_PK:+.4f} dWD={wd - OFFICIAL_WD:+.4f} {verdict}"
        )


if __name__ == "__main__":
    main()
