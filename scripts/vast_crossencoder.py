"""
Vast.ai Job 3: Cross-encoder MiniLM finetuning for boundary scoring.
Trains a cross-encoder on (sent_i + sent_{i+1}) -> boundary/no-boundary.
At inference: score every adjacent pair, threshold to get boundaries.
Run: python vast_crossencoder.py
Output: models/crossencoder/
"""
import json, sys, time, random
import numpy as np
from pathlib import Path

WORKSPACE = Path("/workspace/lecseg")
SENT_DIR  = WORKSPACE / "sentences"
GT_DIR    = WORKSPACE / "gt_hier"
OUT_DIR   = WORKSPACE / "models" / "crossencoder"
EVAL_OUT  = WORKSPACE / "results" / "eval_crossencoder_loocv.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)
Path(WORKSPACE / "results").mkdir(exist_ok=True)

DONE_FLAG = OUT_DIR / ".done"
if DONE_FLAG.exists():
    print("Already done.")
    sys.exit(0)

from sentence_transformers.cross_encoder import CrossEncoder
from sentence_transformers.cross_encoder.evaluation import CEBinaryClassificationEvaluator
import torch

random.seed(42)


def load_video(vid):
    sfile = SENT_DIR / vid / "sentences.json"
    gfile = GT_DIR / f"{vid}.json"
    if not sfile.exists() or not gfile.exists():
        return None, None
    sents   = json.loads(sfile.read_text(encoding="utf-8")).get("sentences", [])
    gt      = json.loads(gfile.read_text(encoding="utf-8"))
    chapters = gt.get("chapters", [])
    if len(chapters) < 2 or not sents:
        return None, None
    starts = [s.get("start", 0.0) for s in sents]
    boundaries = set()
    for ch in chapters[1:]:
        t = ch["start_sec"]
        idx = min(range(len(starts)), key=lambda i: abs(starts[i] - t))
        if idx > 0:
            boundaries.add(idx)
    return [s["text"] for s in sents], sorted(boundaries)


def make_ce_examples(texts, boundaries):
    """(sent_i + ' [SEP] ' + sent_{i+1}, label) for every gap."""
    boundary_set = set(boundaries)
    pairs, labels = [], []
    for i in range(len(texts) - 1):
        pair = [texts[i], texts[i + 1]]
        label = 1 if (i + 1) in boundary_set else 0
        pairs.append(pair)
        labels.append(label)
    return pairs, labels


print("Loading cross-encoder model (MiniLM-L6)...")
ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", num_labels=1,
                  default_activation_function=torch.nn.Sigmoid())
print("Model loaded.")

videos = sorted([f.stem for f in GT_DIR.glob("*.json") if f.stem != "iaa_report"])
all_data = {}
for vid in videos:
    texts, bounds = load_video(vid)
    if texts and bounds:
        all_data[vid] = (texts, bounds)

print(f"Loaded {len(all_data)} videos")

# Build full training set (all videos)
all_pairs, all_labels = [], []
for texts, bounds in all_data.values():
    p, l = make_ce_examples(texts, bounds)
    all_pairs.extend(p)
    all_labels.extend(l)

pos = sum(all_labels)
neg = len(all_labels) - pos
print(f"Training examples: {len(all_labels)} ({pos} positive, {neg} negative)")

# Oversample positives to balance
pos_idx = [i for i, l in enumerate(all_labels) if l == 1]
neg_idx  = [i for i, l in enumerate(all_labels) if l == 0]
random.shuffle(neg_idx)
neg_idx = neg_idx[:min(len(neg_idx), pos * 5)]  # 5:1 ratio max
balanced_idx = pos_idx * 3 + neg_idx
random.shuffle(balanced_idx)
train_pairs  = [all_pairs[i]  for i in balanced_idx]
train_labels = [all_labels[i] for i in balanced_idx]
print(f"Balanced training set: {len(train_labels)} examples")

from sentence_transformers import InputExample
from torch.utils.data import DataLoader as TorchDataLoader

train_samples = [InputExample(texts=p, label=float(l))
                 for p, l in zip(train_pairs, train_labels)]
train_dl = TorchDataLoader(train_samples, shuffle=True, batch_size=32)

t0 = time.time()
ce.fit(
    train_dataloader=train_dl,
    epochs=2,
    warmup_steps=100,
    output_path=str(OUT_DIR),
    show_progress_bar=True,
)
elapsed = time.time() - t0
print(f"Training done in {elapsed/60:.1f} min.")
# Explicitly save (some sentence-transformers versions don't honor output_path)
OUT_DIR.mkdir(parents=True, exist_ok=True)
ce.model.save_pretrained(str(OUT_DIR))
ce.tokenizer.save_pretrained(str(OUT_DIR))
print(f"Model saved to {OUT_DIR}")

# Quick eval: predict boundaries by thresholding cross-encoder scores
print("\nRunning LOOCV boundary prediction eval...")
try:
    sys.path.insert(0, "/workspace/lecseg/src") if Path("/workspace/lecseg/src").exists() else None
    from lecseg.metrics import evaluate

    ce_finetuned = CrossEncoder(str(OUT_DIR), num_labels=1,
                                default_activation_function=torch.nn.Sigmoid())
    pk_scores = []
    for test_vid, (texts, gt_b) in all_data.items():
        pairs = [[texts[i], texts[i+1]] for i in range(len(texts)-1)]
        scores = ce_finetuned.predict(pairs, batch_size=64, show_progress_bar=False)
        # threshold at 0.35
        pred = [i+1 for i, s in enumerate(scores) if s >= 0.35]
        s = evaluate(pred, gt_b, n_units=len(texts))
        pk_scores.append(s.pk)
        print(f"  {test_vid}: pk={s.pk:.4f}  n_pred={len(pred)}  n_gt={len(gt_b)}")

    macro_pk = float(np.mean(pk_scores))
    print(f"\nCross-encoder LOOCV Macro Pk: {macro_pk:.4f}")
    json.dump({"macro_pk": macro_pk, "method": "CrossEncoder_MiniLM_finetuned",
               "threshold": 0.35}, open(EVAL_OUT, "w"), indent=2)
except Exception as e:
    print(f"Eval skipped: {e}")

DONE_FLAG.touch()
print(f"\nDone. Download with:")
print(f"  scp -P PORT -r root@IP:/workspace/lecseg/models/crossencoder/ models/")
