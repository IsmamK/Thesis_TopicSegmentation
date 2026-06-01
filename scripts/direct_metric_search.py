"""Direct Pk/WD-oriented random search over candidate selection features.

Unlike classifier-based candidate rankers, this script samples deterministic
linear scoring functions and selects the one that minimizes segmentation
metrics on training folds. It is intended to test whether direct metric
optimization over existing candidate features can beat the conservative
cross-model baseline.
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.candidate_ranker import (  # noqa: E402
    VideoExample,
    _evaluate_predictions,
    _load_or_build_examples,
    _normalise01,
    _select_boundaries,
    DEFAULT_MODELS,
)


@dataclass(frozen=True)
class Config:
    weights: tuple[float, ...]
    frac: float
    min_seg: int
    nms: int

    @property
    def name(self) -> str:
        w = "_".join(str(round(x, 3)).replace(".", "p") for x in self.weights)
        return f"direct_w{w}_frac{int(self.frac * 100)}_min{self.min_seg}_nms{self.nms}"


def _compact_features(ex: VideoExample) -> np.ndarray:
    if ex.features.size == 0:
        return np.zeros((0, 10), dtype=np.float64)
    source = ex.features[:, 11:]
    density = (source > 0).mean(axis=1) if source.size else np.zeros(len(ex.candidates))
    source_std = source.std(axis=1) if source.size else np.zeros(len(ex.candidates))
    cols = [
        ex.features[:, 1],   # edge distance
        ex.features[:, 4],   # vote
        ex.features[:, 5],   # model agreement
        ex.features[:, 6],   # mean source
        ex.features[:, 7],   # max source
        ex.features[:, 8],   # isolation
        ex.features[:, 9],   # prosody
        ex.features[:, 10],  # shots
        density,
        source_std,
    ]
    mat = np.vstack(cols).T.astype(np.float64)
    return np.apply_along_axis(_normalise01, 0, mat)


def _score(ex: VideoExample, compact: np.ndarray, config: Config) -> np.ndarray:
    if compact.size == 0:
        return np.zeros(0, dtype=np.float64)
    w = np.asarray(config.weights, dtype=np.float64)
    return _normalise01(compact @ w)


def _predict_one(ex: VideoExample, compact: np.ndarray, config: Config) -> list[int]:
    k = max(1, int(round(ex.target_boundaries * config.frac)))
    return _select_boundaries(
        ex.candidates,
        _score(ex, compact, config),
        ex.n_sentences,
        k,
        config.min_seg,
        config.nms,
    )


def _evaluate_config(
    examples: list[VideoExample],
    compact: dict[str, np.ndarray],
    config: Config,
) -> dict[str, float]:
    predictions = {ex.video_id: _predict_one(ex, compact[ex.video_id], config) for ex in examples}
    return _evaluate_predictions(examples, predictions)


def _sample_configs(n: int, seed: int) -> list[Config]:
    rng = np.random.default_rng(seed)
    configs: list[Config] = []
    # Include hand-written anchors.
    anchors = [
        (0.05, 0.45, 0.15, 0.15, 0.25, 0.00, 0.02, 0.02, 0.10, 0.05),
        (0.02, 0.25, 0.25, 0.10, 0.25, 0.05, 0.02, 0.02, 0.20, 0.10),
        (0.05, 0.20, 0.30, 0.15, 0.20, 0.05, 0.00, 0.00, 0.25, 0.10),
    ]
    for weights in anchors:
        for frac in (0.55, 0.60, 0.65, 0.70):
            for min_seg in (8, 10, 11, 12):
                for nms in (2, 5, 8):
                    configs.append(Config(weights, frac, min_seg, nms))

    for _ in range(n):
        # Dirichlet keeps weights positive and interpretable.
        weights = tuple(float(x) for x in rng.dirichlet(np.ones(10) * 0.8))
        frac = float(rng.choice([0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]))
        min_seg = int(rng.choice([6, 8, 10, 11, 12, 14, 16]))
        nms = int(rng.choice([2, 3, 5, 8, 10]))
        configs.append(Config(weights, frac, min_seg, nms))
    return configs


def _global_search(
    examples: list[VideoExample],
    compact: dict[str, np.ndarray],
    configs: list[Config],
) -> list[dict[str, Any]]:
    rows = []
    for config in configs:
        metrics = _evaluate_config(examples, compact, config)
        rows.append({"name": config.name, "config": config.__dict__, **metrics})
    rows.sort(key=lambda row: (row.get("pk", 1.0), row.get("wd", 1.0)))
    return rows


def _leave_one_out(
    examples: list[VideoExample],
    compact: dict[str, np.ndarray],
    configs: list[Config],
    shortlist_size: int,
) -> dict[str, Any]:
    global_rows = _global_search(examples, compact, configs)
    shortlist = [Config(tuple(row["config"]["weights"]), row["config"]["frac"], row["config"]["min_seg"], row["config"]["nms"]) for row in global_rows[:shortlist_size]]
    predictions: dict[str, list[int]] = {}
    chosen: dict[str, str] = {}
    for holdout in examples:
        train = [ex for ex in examples if ex.video_id != holdout.video_id]
        best_config = min(
            shortlist,
            key=lambda cfg: (
                _evaluate_config(train, compact, cfg)["pk"],
                _evaluate_config(train, compact, cfg)["wd"],
            ),
        )
        chosen[holdout.video_id] = best_config.name
        predictions[holdout.video_id] = _predict_one(holdout, compact[holdout.video_id], best_config)
    return {
        "metrics": _evaluate_predictions(examples, predictions),
        "chosen": chosen,
        "global_shortlist": global_rows[:shortlist_size],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    examples = _load_or_build_examples(args.data_dir, tuple(args.models), args.cache, args.verbose)
    compact = {ex.video_id: _compact_features(ex) for ex in examples}
    configs = _sample_configs(args.samples, args.seed)
    global_rows = _global_search(examples, compact, configs)
    loo = _leave_one_out(examples, compact, configs, args.shortlist)
    return {
        "meta": {
            "n_videos": len(examples),
            "samples": args.samples,
            "seed": args.seed,
            "shortlist": args.shortlist,
            "models": list(args.models),
            "eval_gt": "youtube_chapters",
        },
        "best_global": global_rows[0],
        "top_global": global_rows[:25],
        "leave_one_out": loo,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "candidate_ranker_examples.pkl")
    parser.add_argument("--models", nargs="*", default=list(DEFAULT_MODELS))
    parser.add_argument("--samples", type=int, default=400)
    parser.add_argument("--shortlist", type=int, default=60)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_direct_metric_search.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    results = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    best = results["best_global"]
    loo = results["leave_one_out"]["metrics"]
    print(f"Wrote {args.output}")
    print(
        "Best global: {name} Pk={pk:.4f} WD={wd:.4f} BS={boundary_similarity:.4f} F1@2={f1_tol2:.4f}".format(
            **best
        )
    )
    print(
        "LOO selected: Pk={pk:.4f} WD={wd:.4f} BS={boundary_similarity:.4f} F1@2={f1_tol2:.4f}".format(
            **loo
        )
    )


if __name__ == "__main__":
    main()
