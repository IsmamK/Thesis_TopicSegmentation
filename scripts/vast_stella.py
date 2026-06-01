"""
Vast.ai Job 1: Stella 1.5B embeddings for all 30 lecture videos.
Run: python vast_stella.py
Output: embeddings/stella/<video_id>/embeddings.npy
"""
import json, os, sys, time
import numpy as np
from pathlib import Path

WORKSPACE = Path("/workspace/lecseg")
SENT_DIR  = WORKSPACE / "sentences"
OUT_DIR   = WORKSPACE / "embeddings" / "stella"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DONE_FLAG = OUT_DIR / ".done"
if DONE_FLAG.exists():
    print("Already done. Exiting.")
    sys.exit(0)

print("Loading Stella 1.5B model...")
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("dunzhang/stella_en_1.5B_v5", trust_remote_code=True)
model.max_seq_length = 512
print("Model loaded.")

video_dirs = sorted([d for d in SENT_DIR.iterdir() if d.is_dir()])
total = len(video_dirs)
print(f"Embedding {total} videos with Stella 1.5B...")

for i, vdir in enumerate(video_dirs):
    vid = vdir.name
    out_path = OUT_DIR / vid / "embeddings.npy"
    if out_path.exists():
        print(f"[{i+1}/{total}] {vid} — skip (exists)")
        continue
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sfile = vdir / "sentences.json"
    if not sfile.exists():
        print(f"[{i+1}/{total}] {vid} — no sentences, skip")
        continue

    data = json.loads(sfile.read_text(encoding="utf-8"))
    texts = [s["text"] for s in data.get("sentences", [])]
    if not texts:
        continue

    t0 = time.time()
    vecs = model.encode(texts, batch_size=32, show_progress_bar=False,
                        normalize_embeddings=True, convert_to_numpy=True)
    elapsed = time.time() - t0
    np.save(str(out_path), vecs.astype(np.float32))
    print(f"[{i+1}/{total}] {vid}: {vecs.shape} in {elapsed:.1f}s")

DONE_FLAG.touch()
print(f"\nDone. All Stella embeddings saved to {OUT_DIR}")
print("Run scp to download: scp -P PORT -r root@IP:/workspace/lecseg/embeddings/stella/ data/embeddings/")
