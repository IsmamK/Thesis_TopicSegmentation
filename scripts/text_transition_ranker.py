"""Text-transition candidate ranker for lecture topic segmentation.

This experiment extends the existing candidate-ranker features with lexical
transition cues from the transcript. The prior experiments show that candidate
coverage is high but selection is weak; this script tests whether lecture-
specific discourse and local lexical novelty features improve boundary choice.
"""

from __future__ import annotations

import argparse
import json
import math
import pickle
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.candidate_ranker import (  # noqa: E402
    DEFAULT_MODELS,
    MAX_SENTENCES,
    VideoExample,
    _evaluate_predictions,
    _load_manifest,
    _load_or_build_examples,
    _normalise01,
    _read_json,
    _select_boundaries,
)


START_MARKERS = (
    "now",
    "okay",
    "ok",
    "alright",
    "so",
    "next",
    "then",
    "first",
    "second",
    "third",
    "finally",
    "let us",
    "let's",
    "moving on",
    "we will",
    "we're going",
    "i will",
    "i'm going",
    "in this section",
    "in this part",
    "today",
)

RECAP_MARKERS = (
    "to summarize",
    "in summary",
    "so far",
    "we have seen",
    "we've seen",
    "remember",
    "recall",
    "this completes",
    "that completes",
)

TITLE_MARKERS = (
    "definition",
    "theorem",
    "example",
    "problem",
    "chapter",
    "section",
    "topic",
    "introduction",
    "conclusion",
)

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_'-]*")


def _load_sentence_texts(data_dir: Path, video_id: str) -> list[str]:
    obj = _read_json(data_dir / "sentences" / video_id / "sentences.json")
    return [str(row.get("text", "")) for row in obj.get("sentences", [])[:MAX_SENTENCES]]


def _tokens(text: str) -> set[str]:
    return {tok.lower() for tok in TOKEN_RE.findall(text) if len(tok) > 2}


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    low = text.lower()
    return sum(1 for marker in markers if marker in low)


def _starts_with_marker(text: str, markers: tuple[str, ...]) -> float:
    low = text.strip().lower()
    return 1.0 if any(low.startswith(marker) for marker in markers) else 0.0


def _text_features_for_example(ex: VideoExample, texts: list[str], window: int = 4) -> np.ndarray:
    rows: list[list[float]] = []
    n = min(ex.n_sentences, len(texts))
    token_cache = [_tokens(t) for t in texts[:n]]
    for b in ex.candidates:
        b = int(b)
        left_start = max(0, b - window)
        right_end = min(n, b + window)
        left_text = " ".join(texts[left_start:b])
        right_text = " ".join(texts[b:right_end])
        prev_text = texts[b - 1] if 0 <= b - 1 < n else ""
        next_text = texts[b] if 0 <= b < n else ""

        left_tokens: set[str] = set()
        right_tokens: set[str] = set()
        for i in range(left_start, b):
            left_tokens.update(token_cache[i])
        for i in range(b, right_end):
            right_tokens.update(token_cache[i])

        union = left_tokens | right_tokens
        inter = left_tokens & right_tokens
        jaccard = len(inter) / max(1, len(union))
        novelty = 1.0 - jaccard
        new_right = len(right_tokens - left_tokens) / max(1, len(right_tokens))
        left_only = len(left_tokens - right_tokens) / max(1, len(left_tokens))

        prev_len = len(prev_text.split())
        next_len = len(next_text.split())
        len_ratio = abs(next_len - prev_len) / max(1, prev_len + next_len)

        rows.append(
            [
                _starts_with_marker(next_text, START_MARKERS),
                _count_markers(next_text[:160], START_MARKERS) / 3.0,
                _count_markers(prev_text[-220:] + " " + next_text[:220], RECAP_MARKERS) / 2.0,
                _count_markers(next_text[:220], TITLE_MARKERS) / 2.0,
                novelty,
                new_right,
                left_only,
                len_ratio,
                math.log1p(max(0, b)),
                math.log1p(max(0, n - b)),
            ]
        )
    return np.asarray(rows, dtype=np.float64)


def _make_augmented_examples(data_dir: Path, examples: list[VideoExample]) -> dict[str, np.ndarray]:
    text_features: dict[str, np.ndarray] = {}
    for ex in examples:
        texts = _load_sentence_texts(data_dir, ex.video_id)
        feats = _text_features_for_example(ex, texts)
        if feats.size:
            # Normalize only continuous lexical novelty/count columns where useful.
            feats[:, 1:] = np.apply_along_axis(_normalise01, 0, feats[:, 1:])
        text_features[ex.video_id] = feats
    return text_features


def _train_leave_one_out(
    examples: list[VideoExample],
    augmented: dict[str, np.ndarray],
    label_name: str,
) -> dict[str, dict[str, np.ndarray]]:
    from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    labels_attr = "labels_tol2" if label_name == "tol2" else "labels_tol3"
    factories = {
        "logreg_text": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(class_weight="balanced", C=0.25, max_iter=2000, random_state=29),
        ),
        "gb_text": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            GradientBoostingClassifier(n_estimators=120, learning_rate=0.04, max_depth=2, random_state=29),
        ),
        "extra_text": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            ExtraTreesClassifier(
                n_estimators=500,
                min_samples_leaf=3,
                class_weight="balanced",
                random_state=29,
                n_jobs=-1,
            ),
        ),
        "rf_text": lambda: make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(
                n_estimators=350,
                min_samples_leaf=3,
                class_weight="balanced_subsample",
                random_state=29,
                n_jobs=-1,
            ),
        ),
    }

    scores: dict[str, dict[str, np.ndarray]] = {name: {} for name in factories}
    for holdout in examples:
        train = [ex for ex in examples if ex.video_id != holdout.video_id]
        x_train = np.vstack([np.hstack([ex.features, augmented[ex.video_id]]) for ex in train])
        y_train = np.concatenate([getattr(ex, labels_attr) for ex in train])
        x_holdout = np.hstack([holdout.features, augmented[holdout.video_id]])
        for name, factory in factories.items():
            clf = factory()
            clf.fit(x_train, y_train)
            if hasattr(clf, "predict_proba"):
                scores[name][holdout.video_id] = clf.predict_proba(x_holdout)[:, 1]
            else:
                scores[name][holdout.video_id] = _normalise01(clf.decision_function(x_holdout))
    return scores


def _evaluate_score_family(
    examples: list[VideoExample],
    score_by_video: dict[str, np.ndarray],
    prefix: str,
) -> dict[str, dict[str, float]]:
    results: dict[str, dict[str, float]] = {}
    for frac in (0.35, 0.45, 0.55, 0.65, 0.70, 0.75):
        for min_seg in (8, 10, 11, 12, 15):
            for nms in (2, 3, 5, 8):
                predictions = {}
                for ex in examples:
                    k = max(1, int(round(ex.target_boundaries * frac)))
                    predictions[ex.video_id] = _select_boundaries(
                        ex.candidates,
                        score_by_video[ex.video_id],
                        ex.n_sentences,
                        k,
                        min_seg,
                        nms,
                    )
                name = f"{prefix}_frac{int(frac * 100)}_min{min_seg}_nms{nms}"
                results[name] = _evaluate_predictions(examples, predictions)
    return results


def run(data_dir: Path, cache_path: Path | None, verbose: bool) -> dict[str, Any]:
    examples = _load_or_build_examples(data_dir, DEFAULT_MODELS, cache_path, verbose)
    augmented = _make_augmented_examples(data_dir, examples)

    results: dict[str, Any] = {
        "meta": {
            "n_videos": len(examples),
            "models": list(DEFAULT_MODELS),
            "eval_gt": "youtube_chapters",
            "training": "leave_one_video_out",
            "features": "candidate_ranker_plus_text_transition",
        },
        "methods": {},
    }

    for label_name in ("tol2", "tol3"):
        loo_scores = _train_leave_one_out(examples, augmented, label_name)
        for clf_name, score_map in loo_scores.items():
            results["methods"].update(_evaluate_score_family(examples, score_map, f"{clf_name}_{label_name}"))

    best = min(results["methods"].items(), key=lambda item: (item[1]["pk"], item[1]["wd"]))
    results["best_method"] = {"name": best[0], **best[1]}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_text_transition_ranker.json")
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "candidate_ranker_examples.pkl")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    cache_path = None if args.no_cache else args.cache
    results = run(args.data_dir, cache_path, args.verbose)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {args.output}")
    print(
        "Best: {name} Pk={pk:.4f} WD={wd:.4f} BS={boundary_similarity:.4f} F1@2={f1_tol2:.4f}".format(
            **results["best_method"]
        )
    )


if __name__ == "__main__":
    main()
