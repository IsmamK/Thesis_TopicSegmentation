"""
Full LECSEG pipeline — end-to-end lecture segmentation.

Runs:
    T15: Sentence splitting from downloaded transcripts
    T19: Text embedding
    T21: Feature alignment
    T26+T25: Two-stage boundary prediction with RWF
    T27: Hierarchical output
    T28: LLM titling (optional, requires Ollama)
    T29: Evaluation against ground truth (if available)

Usage:
    # Process all videos
    python scripts/pipeline.py

    # Process a single video
    python scripts/pipeline.py --video 7K1sB05pE0A

    # Skip LLM titling
    python scripts/pipeline.py --no-llm

    # Use specific embedding model
    python scripts/pipeline.py --model sbert
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lecseg.preprocess.sentence_split import split_transcript
from lecseg.features.text_embeddings import embed_sentences
from lecseg.features.alignment import align_to_sentences
from lecseg.models.boundary_predictor import TwoStageBoundaryPredictor
from lecseg.models.hierarchical import HierarchicalSegmenter
from lecseg.metrics import evaluate

TRANSCRIPTS_DIR = ROOT / "data" / "transcripts"
SENTENCES_DIR = ROOT / "data" / "sentences"
EMBEDDINGS_DIR = ROOT / "data" / "embeddings"
PREDICTIONS_DIR = ROOT / "data" / "predictions"
GT_HIER = ROOT / "data" / "gt_hier"

import numpy as np


def process_video(
    video_id: str,
    model: str = "mpnet",
    n_chapters: int | None = None,
    n_subtopics: int | None = None,
    use_llm: bool = False,
    force: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Run full pipeline for a single video.

    Returns:
        Result dict with predictions and optional evaluation.
    """
    transcript_path = TRANSCRIPTS_DIR / video_id / "transcript.json"
    if not transcript_path.exists():
        if verbose:
            print(f"  {video_id}: No transcript found, skipping")
        return {"error": "no transcript"}

    # T15: Sentence splitting
    sentences_path = SENTENCES_DIR / video_id / "sentences.json"
    if not sentences_path.exists() or force:
        if verbose:
            print(f"  {video_id}: Splitting sentences...")
        sentences = split_transcript(transcript_path, sentences_path)
    else:
        data = json.loads(sentences_path.read_text(encoding="utf-8"))
        sentences = data.get("sentences", [])

    N = len(sentences)
    if N < 5:
        return {"error": f"too few sentences: {N}"}

    # T19: Embeddings
    emb_path = EMBEDDINGS_DIR / model / video_id / "embeddings.npy"
    if emb_path.exists() and not force:
        vecs = np.load(str(emb_path)).astype(np.float32)
    else:
        if verbose:
            print(f"  {video_id}: Computing {model} embeddings...")
        texts = [s["text"] for s in sentences]
        vecs = embed_sentences(texts, model=model)
        emb_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(emb_path), vecs)

    # Determine target segment counts
    gt = _load_gt(video_id)
    if n_chapters is None:
        n_chapters = len(gt.get("chapters", [])) + 1 if gt else max(2, N // 40)
    if n_subtopics is None:
        n_subtopics = len(gt.get("subtopics", [])) + 1 if gt else max(3, N // 20)

    # T26+T25: Two-stage prediction
    if verbose:
        print(f"  {video_id}: Segmenting (n_ch={n_chapters}, n_sub={n_subtopics})...")

    seg = HierarchicalSegmenter()
    tree = seg.segment(vecs, n_subtopics=n_subtopics, n_chapters=n_chapters)

    # T28: LLM titling (optional)
    titles = None
    if use_llm:
        try:
            from lecseg.refine.llm_refine import LLMRefiner
            refiner = LLMRefiner()
            if refiner._is_available():
                if verbose:
                    print(f"  {video_id}: LLM titling...")
                sent_texts = [s["text"] for s in sentences]
                titles = refiner.title_segments(sent_texts, tree.subtopics)
            else:
                if verbose:
                    print(f"  {video_id}: Ollama not available, skipping LLM titles")
        except Exception as e:
            if verbose:
                print(f"  {video_id}: LLM titling failed: {e}")

    # Save predictions
    result = {
        "video_id": video_id,
        "n_sentences": N,
        "model": model,
        "n_chapters": tree.n_chapters(),
        "n_subtopics": tree.n_subtopics(),
        "chapters": tree.chapters,
        "subtopics": tree.subtopics,
        "titles": titles,
    }

    pred_path = PREDICTIONS_DIR / f"{video_id}.json"
    pred_path.parent.mkdir(parents=True, exist_ok=True)
    pred_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # T29: Evaluation
    if gt:
        ref_ch = gt.get("chapters", [])
        if ref_ch:
            scores = evaluate(tree.chapters, ref_ch, n_units=N)
            result["eval"] = scores.as_dict()
            if verbose:
                print(f"  {video_id}: Pk={scores.pk:.3f}  WD={scores.wd:.3f}  "
                      f"F1={scores.f1:.3f}")

    return result


def _load_gt(video_id: str) -> dict | None:
    p = GT_HIER / f"{video_id}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d if d.get("status") in ("reviewed", "done") else None


def process_all(
    model: str = "mpnet",
    use_llm: bool = False,
    force: bool = False,
    verbose: bool = False,
) -> dict:
    """Process all videos with available transcripts."""
    video_ids = [p.parent.name for p in sorted(TRANSCRIPTS_DIR.glob("*/transcript.json"))]

    if not video_ids:
        print("No transcripts found. Run T14 (Whisper transcription) first.")
        return {}

    print(f"Processing {len(video_ids)} videos with model={model}...")
    results = {}

    for vid in video_ids:
        if verbose:
            print(f"\n{vid}:")
        result = process_video(vid, model=model, use_llm=use_llm, force=force,
                               verbose=verbose)
        results[vid] = result

    # Summary
    successful = [v for v, r in results.items() if "error" not in r]
    evaluated = [v for v, r in results.items() if "eval" in r]
    print(f"\nDone: {len(successful)}/{len(video_ids)} processed, "
          f"{len(evaluated)} evaluated")

    if evaluated:
        all_pk = [results[v]["eval"]["pk"] for v in evaluated]
        all_f1 = [results[v]["eval"]["f1"] for v in evaluated]
        print(f"Mean Pk:  {sum(all_pk)/len(all_pk):.4f}")
        print(f"Mean F1:  {sum(all_f1)/len(all_f1):.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run LECSEG pipeline")
    parser.add_argument("--video", default=None, help="Process single video ID")
    parser.add_argument("--model", default="mpnet",
                        choices=["sbert", "mpnet", "e5", "bge"],
                        help="Embedding model")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM titling")
    parser.add_argument("--force", action="store_true",
                        help="Recompute even if cached")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.video:
        result = process_video(
            args.video,
            model=args.model,
            use_llm=not args.no_llm,
            force=args.force,
            verbose=args.verbose,
        )
        print(json.dumps(result, indent=2))
    else:
        process_all(
            model=args.model,
            use_llm=not args.no_llm,
            force=args.force,
            verbose=args.verbose,
        )


if __name__ == "__main__":
    main()
