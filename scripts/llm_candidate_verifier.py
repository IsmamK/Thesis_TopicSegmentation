"""Same-dataset local-LLM candidate-boundary verifier.

This experiment asks a local Ollama model to verify a shortlist of plausible
candidate boundaries from the existing candidate generator. It is intentionally
kept separate from the official result pipeline until its metrics justify
promotion.

The script is designed to be restartable:
- candidate features come from ``scripts/candidate_ranker.py``;
- every LLM answer is cached under ``data/llm_cache/candidate_verifier``;
- the final report is written to ``results/``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from candidate_ranker import (  # noqa: E402
    DEFAULT_MODELS,
    _evaluate_predictions,
    _load_or_build_examples,
    _normalise01,
    _select_boundaries,
    _vote_scores,
)

OLLAMA_URL = "http://localhost:11434/api/generate"


def _safe_model_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model)


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _ollama_generate(model: str, prompt: str, timeout: int = 90) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 12,
                "top_p": 0.8,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return str(result.get("response", "")).strip()


def _is_ollama_available() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=5)
        return True
    except Exception:
        return False


def _load_sentence_texts(video_id: str, n: int) -> list[str]:
    path = ROOT / "data" / "sentences" / video_id / "sentences.json"
    obj = _read_json(path, {})
    return [str(row.get("text", "")) for row in obj.get("sentences", [])[:n]]


def _candidate_prompt(texts: list[str], boundary: int, context: int) -> str:
    lo = max(0, boundary - context)
    hi = min(len(texts), boundary + context)
    before_rows = [
        f"{idx + 1}. {texts[idx]}"
        for idx in range(lo, min(boundary, len(texts)))
    ]
    after_rows = [
        f"{idx + 1}. {texts[idx]}"
        for idx in range(boundary, hi)
    ]
    before = "\n".join(before_rows)[-1400:]
    after = "\n".join(after_rows)[:1400]
    return (
        "You are checking lecture chapter boundaries.\n"
        "A good boundary means the lecturer begins a new major topic or "
        "pedagogical section, not just a continuation, example, or aside.\n\n"
        f"BEFORE candidate boundary after sentence {boundary}:\n{before}\n\n"
        f"AFTER candidate boundary starting sentence {boundary + 1}:\n{after}\n\n"
        "Question: should there be a chapter/topic boundary here?\n"
        "Reply with exactly one token: YES or NO."
    )


def _parse_score(response: str) -> float:
    text = response.strip().upper()
    if re.search(r"\bYES\b", text):
        return 1.0
    if re.search(r"\bNO\b", text):
        return 0.0
    return 0.5


def _shortlist_indices(vote_scores: np.ndarray, max_candidates: int) -> np.ndarray:
    if vote_scores.size == 0:
        return np.asarray([], dtype=np.int64)
    limit = min(max_candidates, vote_scores.size)
    return np.asarray(np.argsort(-vote_scores)[:limit], dtype=np.int64)


def _verify_candidates(
    examples,
    model: str,
    max_candidates: int,
    context: int,
    cache_path: Path,
    sleep_s: float,
    verbose: bool,
) -> dict[str, np.ndarray]:
    if not _is_ollama_available():
        raise RuntimeError("Ollama is not reachable at http://localhost:11434")

    cache = _read_json(cache_path, {})
    changed = False
    scores_by_video: dict[str, np.ndarray] = {}

    for ex in examples:
        base_scores = _vote_scores(ex)
        scores = np.zeros(len(ex.candidates), dtype=np.float64)
        shortlisted = set(int(i) for i in _shortlist_indices(base_scores, max_candidates))
        texts = _load_sentence_texts(ex.video_id, ex.n_sentences)
        video_cache = cache.setdefault(ex.video_id, {})

        for idx, boundary in enumerate(ex.candidates):
            if idx not in shortlisted:
                continue
            key = str(int(boundary))
            if key not in video_cache:
                prompt = _candidate_prompt(texts, int(boundary), context)
                try:
                    response = _ollama_generate(model, prompt)
                except (urllib.error.URLError, TimeoutError) as exc:
                    response = f"ERROR: {exc}"
                video_cache[key] = {
                    "boundary": int(boundary),
                    "response": response,
                    "score": _parse_score(response),
                }
                changed = True
                if sleep_s > 0:
                    time.sleep(sleep_s)
            scores[idx] = float(video_cache[key].get("score", 0.5))

        scores_by_video[ex.video_id] = scores
        if verbose:
            yes = int(np.sum(scores > 0.5))
            print(f"{ex.video_id}: verified={len(shortlisted)} yes={yes}")
        if changed:
            _write_json(cache_path, cache)
            changed = False

    _write_json(cache_path, cache)
    return scores_by_video


def _evaluate_combinations(examples, llm_scores, max_candidates: int) -> dict[str, dict[str, float]]:
    vote_by_video = {ex.video_id: _vote_scores(ex) for ex in examples}
    results: dict[str, dict[str, float]] = {}
    for alpha in (0.00, 0.25, 0.50, 0.75, 1.00):
        for frac in (0.55, 0.65, 0.75, 0.85, 1.00):
            for min_seg in (8, 10, 12, 15):
                for nms in (2, 5, 8):
                    predictions = {}
                    for ex in examples:
                        base = vote_by_video[ex.video_id]
                        llm = llm_scores[ex.video_id]
                        combined = _normalise01(((1.0 - alpha) * base) + (alpha * llm))
                        # Restrict to the same LLM-reviewed shortlist when alpha > 0.
                        if alpha > 0:
                            mask = np.zeros_like(combined)
                            idx = _shortlist_indices(base, max_candidates)
                            mask[idx] = 1.0
                            combined = combined * mask
                        k = max(1, int(round(ex.target_boundaries * frac)))
                        predictions[ex.video_id] = _select_boundaries(
                            ex.candidates,
                            combined,
                            ex.n_sentences,
                            k,
                            min_seg,
                            nms,
                        )
                    name = (
                        f"llm_vote_a{int(alpha * 100):03d}_"
                        f"frac{int(frac * 100)}_min{min_seg}_nms{nms}"
                    )
                    results[name] = _evaluate_predictions(examples, predictions)
    return results


def run(args: argparse.Namespace) -> dict[str, Any]:
    examples = _load_or_build_examples(
        args.data_dir,
        tuple(args.models),
        args.cache,
        args.verbose,
    )
    if args.limit_videos is not None:
        examples = examples[: args.limit_videos]
    cache_path = args.llm_cache / f"{_safe_model_name(args.model)}_ctx{args.context}_top{args.max_candidates}.json"
    llm_scores = _verify_candidates(
        examples,
        args.model,
        args.max_candidates,
        args.context,
        cache_path,
        args.sleep,
        args.verbose,
    )
    methods = _evaluate_combinations(examples, llm_scores, args.max_candidates)
    best = min(methods.items(), key=lambda kv: (kv[1]["pk"], kv[1]["wd"]))
    return {
        "meta": {
            "n_videos": len(examples),
            "limit_videos": args.limit_videos,
            "model": args.model,
            "models": args.models,
            "context": args.context,
            "max_candidates": args.max_candidates,
            "llm_cache": str(cache_path.relative_to(ROOT)),
            "eval_gt": "youtube_chapters",
            "note": "Diagnostic local-LLM candidate verifier. Promote only when run on the full official benchmark.",
        },
        "methods": methods,
        "best_method": {"name": best[0], **best[1]},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--models", nargs="*", default=list(DEFAULT_MODELS))
    parser.add_argument("--cache", type=Path, default=ROOT / "results" / "llm_candidate_ranker_examples.pkl")
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--context", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=24)
    parser.add_argument("--limit-videos", type=int, default=None)
    parser.add_argument("--llm-cache", type=Path, default=ROOT / "data" / "llm_cache" / "candidate_verifier")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "eval_llm_candidate_verifier.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    report = run(args)
    _write_json(args.output, report)
    best = report["best_method"]
    print(f"Wrote {args.output}")
    print(
        f"Best: {best['name']} "
        f"Pk={best['pk']:.4f} WD={best['wd']:.4f} "
        f"BS={best['boundary_similarity']:.4f} F1@2={best['f1_tol2']:.4f}"
    )


if __name__ == "__main__":
    main()
