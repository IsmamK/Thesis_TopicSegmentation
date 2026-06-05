"""Perplexity-based boundary scorer using GPT-2.

Computes sentence perplexity conditioned on the previous N sentences using GPT-2.
A sharp perplexity spike indicates a topic shift (the model is surprised by the
new sentence given the context). Used as a segmentation signal or added to
ablation table as a novel complementary feature.

Usage:
    python scripts/perplexity_segmenter.py [--context 5] [--window 3] [--verbose]
"""

import argparse
import json
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from lecseg.metrics import evaluate

import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer


def load_gpt2(device="cpu"):
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    model.eval()
    model.to(device)
    return tokenizer, model


def sentence_perplexity(text: str, context: str, tokenizer, model, device="cpu",
                         max_len: int = 512) -> float:
    """Compute cross-entropy of `text` given `context` prefix."""
    full_text = context + " " + text if context else text
    inputs = tokenizer(full_text, return_tensors="pt", truncation=True,
                       max_length=max_len).to(device)
    context_ids = tokenizer(context, return_tensors="pt",
                             truncation=True, max_length=max_len - 20
                             )["input_ids"] if context else None
    n_context = context_ids.shape[1] if context_ids is not None else 0
    input_ids = inputs["input_ids"]
    n_total = input_ids.shape[1]

    if n_total - n_context <= 0:
        return 0.0

    with torch.no_grad():
        outputs = model(input_ids, labels=input_ids)
        # Per-token loss — we want loss only on the target (non-context) tokens
        logits = outputs.logits  # (1, seq_len, vocab)
        # shift: labels are input_ids[1:], logits are [:-1]
        shift_logits = logits[:, :-1, :].contiguous()
        shift_labels = input_ids[:, 1:].contiguous()
        loss_fn = torch.nn.CrossEntropyLoss(reduction="none")
        losses = loss_fn(shift_logits.view(-1, shift_logits.size(-1)),
                         shift_labels.view(-1))
        # Take loss only on target tokens (after context)
        target_start = max(0, n_context - 1)
        target_losses = losses[target_start:]
        if len(target_losses) == 0:
            return 0.0
        return float(target_losses.mean().exp().item())


def perplexity_scores(texts: list[str], tokenizer, model, context_size: int = 5,
                       device: str = "cpu") -> np.ndarray:
    """Compute per-sentence perplexity with rolling context window."""
    n = len(texts)
    scores = np.zeros(n)
    for i in range(1, n):
        ctx_start = max(0, i - context_size)
        context = " ".join(texts[ctx_start:i])
        scores[i] = sentence_perplexity(texts[i], context, tokenizer, model, device)
    return scores


def smooth(scores: np.ndarray, w: int = 3) -> np.ndarray:
    """Gaussian-like smooth to reduce noise."""
    kernel = np.array([0.25, 0.5, 0.25]) if w == 3 else np.ones(w) / w
    return np.convolve(scores, kernel, mode="same")


def pick_boundaries(scores: np.ndarray, n_targets: int, min_len: int = 5) -> list[int]:
    n = len(scores)
    s = scores.copy()
    s[:min_len] = 0.0
    s[n - min_len:] = 0.0
    boundaries = []
    s_work = s.copy()
    for _ in range(n_targets):
        idx = int(np.argmax(s_work))
        if s_work[idx] <= 0:
            break
        boundaries.append(idx)
        for d in range(-min_len, min_len + 1):
            j = idx + d
            if 0 <= j < n:
                s_work[j] = 0.0
    return sorted(boundaries)


def run_video(vid_id: str, gt_path: Path, tokenizer, model, device: str,
              context_size: int, window: int, min_len: int,
              verbose: bool = False) -> dict | None:
    sent_path = Path(f"data/sentences/{vid_id}/sentences.json")
    if not sent_path.exists():
        return None
    sents = json.load(open(sent_path, encoding="utf-8"))["sentences"]
    texts = [s["text"] for s in sents]

    gt_file = gt_path / f"{vid_id}.json"
    if not gt_file.exists():
        return None
    gt_data = json.load(open(gt_file, encoding="utf-8"))
    boundaries_sec = gt_data.get("boundaries_sec", [])
    if not boundaries_sec:
        return None

    starts = np.array([s["start"] for s in sents])
    ref_boundaries = sorted(set(
        max(1, min(int(np.searchsorted(starts, float(t), side="left")), len(sents) - 1))
        for t in boundaries_sec
    ))

    # Cap for speed (perplexity is slow)
    cap = min(len(texts), 200)
    texts_use = texts[:cap]
    n = len(texts_use)
    ref_cap = [b for b in ref_boundaries if b < n]

    n_targets = max(1, len(ref_cap))

    if verbose:
        print(f"  {vid_id}: {n} sentences (capped), {len(ref_boundaries)} GT boundaries")

    perp = perplexity_scores(texts_use, tokenizer, model, context_size, device)
    perp_smooth = smooth(perp, window)

    boundaries = pick_boundaries(perp_smooth, n_targets, min_len)
    if not boundaries:
        return None

    scores = evaluate(boundaries, ref_cap, n_units=n)
    return {
        "pk": scores.pk, "wd": scores.wd,
        "boundary_similarity": scores.boundary_similarity,
        "f1": scores.f1,
        "n_boundaries": len(boundaries),
        "n_gt_boundaries": len(ref_cap),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=int, default=5, help="Context sentences for perplexity")
    parser.add_argument("--window", type=int, default=3, help="Smoothing window")
    parser.add_argument("--min-len", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="Max videos (0=all, use 5 for quick test)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading GPT-2 on {device}...")
    tokenizer, model = load_gpt2(device)

    gt_path = Path("data/gt")
    manifest = [json.loads(l) for l in open("data/manifest.jsonl", encoding="utf-8")]
    vids = [v["id"] for v in manifest]
    if args.limit:
        vids = vids[:args.limit]

    print(f"Running perplexity segmenter on {len(vids)} videos "
          f"(context={args.context}, window={args.window}, min_len={args.min_len})...")
    print("NOTE: each video is capped at 200 sentences for speed.")

    results = {}
    for i, vid_id in enumerate(vids):
        if args.verbose:
            print(f"[{i+1}/{len(vids)}]", end=" ")
        r = run_video(vid_id, gt_path, tokenizer, model, device,
                      args.context, args.window, args.min_len, args.verbose)
        if r:
            results[vid_id] = r
            print(f"[{i+1}/{len(vids)}] {vid_id}: Pk={r['pk']:.4f} WD={r['wd']:.4f}")
        else:
            print(f"[{i+1}/{len(vids)}] {vid_id}: SKIP")

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
        "cap_sentences": 200,
        "context_size": args.context,
        "smooth_window": args.window,
    }

    out = {
        "method": "gpt2_perplexity_segmenter",
        "summary": {"gpt2_perplexity": summary},
        "per_video": results,
    }
    out_path = Path(f"results/eval_perplexity_ctx{args.context}_w{args.window}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"\n== GPT-2 Perplexity Segmenter Results ==")
    print(f"Mean Pk:  {summary['mean_pk']:.4f}")
    print(f"Mean WD:  {summary['mean_wd']:.4f}")
    print(f"Mean BS:  {summary['mean_bs']:.4f}")
    print(f"Mean F1:  {summary['mean_f1']:.4f}")
    print(f"Saved to {out_path}")
    print(f"\nComparison: BGE-divisive baseline Pk=0.3884 | Our best Pk=0.3588")


if __name__ == "__main__":
    main()
