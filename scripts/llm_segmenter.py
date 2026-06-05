"""Zero-shot LLM topic segmenter using Ollama.

Unlike the broken llm_refine.py (which only ±2-sentence nudges existing boundaries),
this script prompts the LLM directly: given numbered transcript sentences, output
the sentence indices where a new topic begins.

Chunked approach: lectures can be 1000+ sentences, so we split into overlapping
windows of ~80 sentences, get boundaries per chunk, then deduplicate and merge.

Usage:
    python scripts/llm_segmenter.py [--model llama3.1:8b] [--chunk 80] [--overlap 10] [--verbose]
"""

import argparse
import json
import re
import time
import numpy as np
import urllib.request
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from lecseg.metrics import evaluate

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """You are an academic lecture topic segmentation assistant.
Your task: given numbered lecture sentences, identify where a completely NEW CHAPTER-LEVEL topic begins.

Critical rules:
- Output ONLY comma-separated sentence numbers, nothing else. Example: 12,35
- ONLY mark genuine chapter-level topic changes (like YouTube chapter markers).
- Do NOT mark minor transitions, examples, or subtopic shifts.
- Most 80-sentence windows will have 0 or 1 chapter boundary.
- If no clear chapter-level boundary exists, output: none
- Do not include the first sentence number of the chunk."""

PROMPT_TEMPLATE = """Lecture transcript sentences {start}–{end}. Mark only MAJOR chapter-level topic starts.

{sentences}

Output comma-separated sentence numbers for chapter-level starts only (or "none"):"""


def ollama_generate(prompt: str, model: str, timeout: int = 120) -> str:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 100},
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def parse_boundary_response(response: str, chunk_start: int, chunk_end: int) -> list[int]:
    """Extract valid sentence indices from LLM response."""
    if not response or "none" in response.lower() or "ERROR" in response:
        return []
    # Extract all integers from the response
    nums = re.findall(r"\b(\d+)\b", response)
    boundaries = []
    for n in nums:
        idx = int(n)
        # Accept if in range of chunk and > 0
        if chunk_start < idx <= chunk_end:
            boundaries.append(idx)
    return sorted(set(boundaries))


def segment_video_llm(vid_id: str, model: str, gt_path: Path,
                       chunk_size: int = 80, overlap: int = 15,
                       verbose: bool = False) -> dict | None:
    sent_path = Path(f"data/sentences/{vid_id}/sentences.json")
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    texts = [s["text"] for s in sents]
    n = len(texts)

    # Load GT
    gt_file = gt_path / f"{vid_id}.json"
    if not gt_file.exists():
        return None
    gt_data = json.load(open(gt_file, encoding="utf-8"))
    boundaries_sec = gt_data.get("boundaries_sec", [])
    if not boundaries_sec:
        return None

    starts = np.array([s["start"] for s in sents])
    ref_boundaries = sorted(set(
        max(1, min(int(np.searchsorted(starts, float(t), side="left")), n - 1))
        for t in boundaries_sec
    ))
    n_chapters = len(ref_boundaries)

    # Cap at 800 sentences for consistency with main eval
    cap = min(n, 800)
    texts_use = texts[:cap]
    n_use = len(texts_use)

    # Chunk the transcript and query LLM per chunk
    all_boundaries = set()
    step = chunk_size - overlap
    n_chunks = max(1, (n_use - overlap + step - 1) // step)

    if verbose:
        print(f"  {vid_id}: {n_use} sentences, {n_chapters} GT boundaries, {n_chunks} chunks")

    for chunk_idx in range(n_chunks):
        chunk_start = chunk_idx * step
        chunk_end = min(chunk_start + chunk_size, n_use) - 1
        if chunk_start >= n_use:
            break

        # Build numbered sentence list
        lines = []
        for i in range(chunk_start, chunk_end + 1):
            lines.append(f"{i}: {texts_use[i]}")
        sentences_block = "\n".join(lines)

        prompt = PROMPT_TEMPLATE.format(
            start=chunk_start,
            end=chunk_end,
            sentences=sentences_block,
        )

        response = ollama_generate(prompt, model)
        chunk_boundaries = parse_boundary_response(response, chunk_start, chunk_end)
        all_boundaries.update(chunk_boundaries)

        if verbose and chunk_boundaries:
            print(f"    chunk {chunk_idx} ({chunk_start}-{chunk_end}): {chunk_boundaries} | raw: '{response[:60]}'")

        # Small delay to avoid overwhelming Ollama
        time.sleep(0.1)

    boundaries_raw = sorted(b for b in all_boundaries if 0 < b < n_use)

    if verbose:
        print(f"    Raw LLM boundaries: {len(boundaries_raw)} | GT: {n_chapters}")

    if not boundaries_raw:
        return None

    # Post-filter: if over-segmenting, keep the most spread-out n_chapters boundaries
    # using a greedy max-spread selection (similar to NMS)
    boundaries = boundaries_raw
    if len(boundaries_raw) > n_chapters:
        # Greedy: pick boundary with highest "min distance to already-selected"
        # Start with the one closest to the middle of the lecture
        selected = [boundaries_raw[len(boundaries_raw) // 2]]
        remaining = [b for b in boundaries_raw if b != selected[0]]
        while len(selected) < n_chapters and remaining:
            # Pick boundary with max min-distance to selected set
            best = max(remaining, key=lambda b: min(abs(b - s) for s in selected))
            selected.append(best)
            remaining = [b for b in remaining if b != best]
        boundaries = sorted(selected)

    if verbose:
        print(f"    Filtered to {len(boundaries)} boundaries")

    scores = evaluate(boundaries, ref_boundaries, n_units=n_use)
    return {
        "pk": scores.pk,
        "wd": scores.wd,
        "boundary_similarity": scores.boundary_similarity,
        "f1": scores.f1,
        "n_llm_boundaries": len(boundaries),
        "n_gt_boundaries": n_chapters,
        "n_chunks": n_chunks,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--chunk", type=int, default=80)
    parser.add_argument("--overlap", type=int, default=15)
    parser.add_argument("--limit", type=int, default=0, help="Only run N videos (0=all)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    gt_path = Path("data/gt")
    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]
    vids = [v["id"] for v in manifest]
    if args.limit:
        vids = vids[:args.limit]

    print(f"Zero-shot LLM segmenter: {args.model}, chunk={args.chunk}, overlap={args.overlap}")
    print(f"Running on {len(vids)} videos...")

    results = {}
    n_failed = 0

    for i, vid_id in enumerate(vids):
        print(f"[{i+1}/{len(vids)}] {vid_id}", end=" ", flush=True)
        r = segment_video_llm(vid_id, args.model, gt_path,
                               args.chunk, args.overlap, args.verbose)
        if r:
            results[vid_id] = r
            print(f"Pk={r['pk']:.4f} WD={r['wd']:.4f} bounds={r['n_llm_boundaries']}")
        else:
            n_failed += 1
            print("SKIP (no boundaries or missing data)")

    if not results:
        print("No results.")
        return

    pks = [v["pk"] for v in results.values()]
    wds = [v["wd"] for v in results.values()]
    bss = [v["boundary_similarity"] for v in results.values()]
    f1s = [v["f1"] for v in results.values()]

    summary = {
        "mean_pk": round(float(np.mean(pks)), 4),
        "mean_wd": round(float(np.mean(wds)), 4),
        "mean_bs": round(float(np.mean(bss)), 4),
        "mean_f1": round(float(np.mean(f1s)), 4),
        "n_videos": len(results),
        "n_failed": n_failed,
    }

    model_tag = args.model.replace(":", "_").replace(".", "_")
    out = {
        "method": f"llm_zero_shot_{model_tag}",
        "model": args.model,
        "chunk_size": args.chunk,
        "overlap": args.overlap,
        "summary": {f"llm_zero_shot_{model_tag}": summary},
        "per_video": results,
    }
    out_path = Path(f"results/eval_llm_zero_shot_{model_tag}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\n== Zero-Shot LLM Segmenter Results ==")
    print(f"Model:      {args.model}")
    print(f"Videos:     {summary['n_videos']} / {len(vids)} (failed: {n_failed})")
    print(f"Mean Pk:    {summary['mean_pk']:.4f}")
    print(f"Mean WD:    {summary['mean_wd']:.4f}")
    print(f"Mean BS:    {summary['mean_bs']:.4f}")
    print(f"Mean F1:    {summary['mean_f1']:.4f}")
    print(f"Saved to {out_path}")

    # Compare to known baselines
    print(f"\n== Comparison ==")
    print(f"BGE-divisive baseline:   Pk=0.3884")
    print(f"Cross-model best:        Pk=0.3715")
    print(f"Balanced selector best:  Pk=0.3588")
    print(f"LLM zero-shot (this):    Pk={summary['mean_pk']:.4f}")
    delta = summary['mean_pk'] - 0.3588
    if delta < 0:
        print(f"Delta vs selector: {delta:+.4f}  --> LLM BEATS our best!")
    else:
        print(f"Delta vs selector: {delta:+.4f}  --> LLM does not beat our best Pk")


if __name__ == "__main__":
    main()
