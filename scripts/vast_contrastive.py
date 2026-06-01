"""
Vast.ai Job 2: Contrastive finetuning of BGE on lecture boundary pairs.
Uses MultipleNegativesRankingLoss — anchor=sentence, positive=next-in-segment,
hard-negative=first-sentence-of-next-segment.
Leave-one-video-out eval at end.
Run: python vast_contrastive.py
Output: models/bge_contrastive/ (saved SentenceTransformer)
"""
import json, os, sys, time, random
import numpy as np
from pathlib import Path

WORKSPACE  = Path("/workspace/lecseg")
SENT_DIR   = WORKSPACE / "sentences"
GT_DIR     = WORKSPACE / "gt_hier"
OUT_DIR    = WORKSPACE / "models" / "bge_contrastive"
EVAL_OUT   = WORKSPACE / "results" / "eval_contrastive_loocv.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)
Path(WORKSPACE / "results").mkdir(exist_ok=True)

DONE_FLAG  = OUT_DIR / ".done"
if DONE_FLAG.exists():
    print("Already done. Exiting.")
    sys.exit(0)

from sentence_transformers import SentenceTransformer, InputExample, losses
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
from torch.utils.data import DataLoader
import torch

random.seed(42)
np.random.seed(42)


def load_video(vid):
    sfile = SENT_DIR / vid / "sentences.json"
    gfile = GT_DIR / f"{vid}.json"
    if not sfile.exists() or not gfile.exists():
        return None, None
    sents = json.loads(sfile.read_text(encoding="utf-8")).get("sentences", [])
    gt    = json.loads(gfile.read_text(encoding="utf-8"))
    chapters = gt.get("chapters", [])
    if len(chapters) < 2 or not sents:
        return None, None
    # Map chapter start_sec -> sentence index
    starts = [s.get("start", 0.0) for s in sents]
    boundaries = set()
    for ch in chapters[1:]:
        t = ch["start_sec"]
        idx = min(range(len(starts)), key=lambda i: abs(starts[i] - t))
        if idx > 0:
            boundaries.add(idx)
    return [s["text"] for s in sents], sorted(boundaries)


def make_training_pairs(texts, boundaries):
    """
    Positive pairs: sentences within same segment (cosine = 1).
    Hard negatives: cross-boundary pairs (cosine = 0).
    Returns list of InputExample(texts=[a, pos], label=1.0)
    and InputExample(texts=[a, neg], label=0.0)
    """
    N = len(texts)
    bounds = [0] + boundaries + [N]
    segments = [list(range(bounds[i], bounds[i+1])) for i in range(len(bounds)-1)]

    positives, negatives = [], []
    for seg_idx, seg in enumerate(segments):
        if len(seg) < 2:
            continue
        # Sample up to 8 positive pairs per segment
        pairs = [(seg[i], seg[j]) for i in range(len(seg)) for j in range(i+1, len(seg))]
        random.shuffle(pairs)
        for a, b in pairs[:8]:
            positives.append(InputExample(texts=[texts[a], texts[b]], label=1.0))
        # Hard negatives: last sentence of this seg vs first of next seg
        if seg_idx + 1 < len(segments) and segments[seg_idx+1]:
            negatives.append(InputExample(
                texts=[texts[seg[-1]], texts[segments[seg_idx+1][0]]], label=0.0))
            # Also anchor = any mid-seg sent vs first-of-next
            mid = seg[len(seg)//2]
            negatives.append(InputExample(
                texts=[texts[mid], texts[segments[seg_idx+1][0]]], label=0.0))

    return positives + negatives


print("Loading BGE base model...")
model = SentenceTransformer("BAAI/bge-base-en-v1.5")
print("Model loaded.")

videos = sorted([f.stem for f in GT_DIR.glob("*.json") if f.stem != "iaa_report"])
all_data = {}
for vid in videos:
    texts, bounds = load_video(vid)
    if texts and bounds:
        all_data[vid] = (texts, bounds)

print(f"Loaded {len(all_data)} videos for training")

# ── Full training on all data (for the final deployed model) ─────────────────
print("\nBuilding training set from all videos...")
all_examples = []
for vid, (texts, bounds) in all_data.items():
    all_examples.extend(make_training_pairs(texts, bounds))

random.shuffle(all_examples)
print(f"Total training examples: {len(all_examples)}")

train_dataloader = DataLoader(all_examples, shuffle=True, batch_size=32)
train_loss = losses.CosineSimilarityLoss(model)

epochs = 3
warmup = int(len(train_dataloader) * epochs * 0.1)
print(f"Training {epochs} epochs ({len(train_dataloader)} steps/epoch, warmup={warmup})...")

t0 = time.time()
model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=epochs,
    warmup_steps=warmup,
    output_path=str(OUT_DIR),
    save_best_model=True,
    show_progress_bar=True,
)
elapsed = time.time() - t0
print(f"Training done in {elapsed/60:.1f} min. Model saved to {OUT_DIR}")

# ── Quick LOOCV eval ─────────────────────────────────────────────────────────
print("\nRunning leave-one-out eval with finetuned model...")
sys.path.insert(0, str(WORKSPACE / "src")) if (WORKSPACE / "src").exists() else None

try:
    from lecseg.models.divisive import divisive_seg
    from lecseg.metrics import evaluate

    finetuned = SentenceTransformer(str(OUT_DIR))
    pk_scores = []
    for test_vid in list(all_data.keys()):
        texts, gt_b = all_data[test_vid]
        vecs = finetuned.encode(texts, batch_size=64, normalize_embeddings=True,
                                convert_to_numpy=True)
        k = len(gt_b) + 1
        pred = divisive_seg(vecs, n_segments=k)
        s = evaluate(pred, gt_b, n_units=len(texts))
        pk_scores.append(s.pk)
        print(f"  {test_vid}: pk={s.pk:.4f}")

    macro_pk = float(np.mean(pk_scores))
    print(f"\nContrastive LOOCV Macro Pk (oracle-k): {macro_pk:.4f}")
    json.dump({"macro_pk_oracle_k": macro_pk, "method": "BGE_contrastive_finetuned",
               "n_videos": len(pk_scores)}, open(EVAL_OUT, "w"), indent=2)
except Exception as e:
    print(f"Eval skipped (lecseg not in path on instance): {e}")
    print("Download model and eval locally instead.")

DONE_FLAG.touch()
print(f"\nAll done. Download with:")
print(f"  scp -P PORT -r root@IP:/workspace/lecseg/models/bge_contrastive/ models/")
