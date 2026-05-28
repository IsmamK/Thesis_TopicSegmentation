"""
T17 + T20 visual feature extraction — batch processor with upload verification.

T17: PaddleOCR v4 slide-text extraction per sentence (GPU:0)
T20: CLIP ViT-B/32 L2-normalised 512-d embeddings (GPU:1 / GPU:0)

Scientific design:
  - Frame at sentence midpoint timestamp for representative content
  - PaddleOCR GPU, confidence threshold 0.5, angle classification
  - CLIP ViT-B/32 with L2 normalisation (standard practice)
  - 3 videos without audio/video marked with zero vectors + metadata flag
"""
from __future__ import annotations
import json, os, shutil, subprocess, threading, time, tempfile
from pathlib import Path
import numpy as np

ROOT     = Path("/root/data")
VID_DIR  = Path("/root/videos")
OUT      = Path("/root/output")
SENT_DIR = ROOT / "sentences"

(OUT / "ocr").mkdir(parents=True, exist_ok=True)
(OUT / "clip").mkdir(parents=True, exist_ok=True)

# Expected sizes in bytes (from local du -b) — used to verify upload completeness
# Derived from local file sizes; allows ±2% tolerance
EXPECTED_MB = {
    "7K1sB05pE0A": 173, "8yT4RZy1t3s": 172, "9N1MxkbFhsc": 185,
    "AMl6E4cLrwE": 140, "D8RRq3TbtHU": 1364, "fsLh-NYhOoU": 478,
    "GR63MMAi-fs": 120, "HtSuA80QTyo": 119, "Hy7ou5R_vjE": 112,
    "j0wJBEZdwLs": 625, "JP7ITIXGpHk": 401, "KlVHqq38KJU": 171,
    "KNwMiydCYA4": 3354, "KOKnWaLiL8w": 127, "lUUte2o2Sn8": None,
    "MGyygiXMzRk": 157, "NK-BxowMIfg": None, "NNnIGh9g6fA": 100,
    "Ns6GB4Dph9U": 105, "oOya3cFmAMc": 217, "oqRU2So6Z2Y": 606,
    "Qw4l1w0rkjs": 168, "Rl0ludWTLxs": 583, "S7TUe5w6RHo": 3154,
    "TjZBTDzGeGg": 174, "uK2eFv7ne_Q": 124, "uO5k9xcD1gU": 184,
    "YdOXS_9_P4U": 792, "zNVQfWC_evg": 272, "jGwO_UgTS7I": None,
}

VIDEO_IDS = list(EXPECTED_MB.keys())

# Videos with no available audio/video (transcribed on GPU server, media not saved)
NO_MEDIA = {"jGwO_UgTS7I", "lUUte2o2Sn8", "NK-BxowMIfg"}

# ── helpers ────────────────────────────────────────────────────────────────────
_t0 = time.time()

def bar(done, total, w=26):
    f = done/total if total else 0
    return "█"*int(f*w) + "░"*(w-int(f*w))

def eta(done, total, elapsed):
    if not done: return "?"
    s = elapsed/done*(total-done)
    return f"{int(s//60)}m{int(s%60)}s" if s < 3600 else f"{s/3600:.1f}h"

def log(tag, done, total, msg=""):
    elapsed = time.time()-_t0
    print(f"[{tag:9s}] [{bar(done,total)}] {done:2d}/{total}  {done/total*100 if total else 0:5.1f}%  ETA {eta(done,total,elapsed)}  {msg}", flush=True)

def is_upload_complete(vid_id: str) -> bool:
    """Check video is fully uploaded (within 2% of expected size)."""
    expected = EXPECTED_MB.get(vid_id)
    if expected is None:
        return False  # no video exists for this ID
    p = VID_DIR / f"{vid_id}.mp4"
    if not p.exists():
        return False
    actual_mb = p.stat().st_size / 1e6
    return actual_mb >= expected * 0.98  # allow 2% tolerance

def extract_frame(video: Path, ts: float, out: str) -> bool:
    r = subprocess.run(
        ["ffmpeg","-y","-ss",f"{ts:.3f}","-i",str(video),
         "-frames:v","1","-q:v","2","-vf","scale=1280:-1",out],
        capture_output=True, timeout=30
    )
    return r.returncode == 0 and os.path.exists(out)

def load_sents(vid_id: str) -> list[dict]:
    f = SENT_DIR / vid_id / "sentences.json"
    if not f.exists(): return []
    raw = json.loads(f.read_text())
    return raw["sentences"] if isinstance(raw, dict) else raw


# ── wait for all uploads ───────────────────────────────────────────────────────
def wait_for_uploads():
    need = [v for v in VIDEO_IDS if EXPECTED_MB[v] is not None]
    print(f"\n[UPLOAD  ] Waiting for {len(need)} video uploads to complete...")
    t0 = time.time()
    last_print = 0
    while True:
        done = [v for v in need if is_upload_complete(v)]
        remaining = [v for v in need if not is_upload_complete(v)]
        now = time.time()
        if now - last_print > 30 or not remaining:
            elapsed = now - t0
            print(f"[UPLOAD  ] [{bar(len(done),len(need))}] {len(done):2d}/{len(need)}  "
                  f"{len(done)/len(need)*100:.0f}%  remaining: {remaining[:4]}{'...' if len(remaining)>4 else ''}",
                  flush=True)
            last_print = now
        if not remaining:
            print(f"[UPLOAD  ] All {len(need)} videos confirmed complete in {time.time()-t0:.0f}s")
            return done
        time.sleep(15)


# ── T17: PaddleOCR ────────────────────────────────────────────────────────────
def run_t17(vid_ids_with_video: list[str], no_media_ids: list[str]):
    print("\n" + "="*65)
    print("T17 — PaddleOCR slide-text extraction (GPU:0)")
    print("="*65)

    # Handle no-media videos first (zero features + flag)
    for vid_id in no_media_ids:
        sents = load_sents(vid_id)
        n = len(sents)
        result = [{"slide_text":"","confidence":0.0,"n_boxes":0,"no_media":True}]*n
        (OUT/"ocr"/f"{vid_id}.json").write_text(json.dumps(result, indent=2))
        print(f"[T17-OCR ] {vid_id}: no media — zero features written ({n} sents)")

    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=True, gpu_id=0,
                        show_log=False, det_db_thresh=0.3, det_db_box_thresh=0.5)
        print("[T17-OCR ] PaddleOCR loaded on GPU:0")
    except Exception as e:
        print(f"[T17-OCR ] FAILED: {e}")
        for vid_id in vid_ids_with_video:
            sents = load_sents(vid_id)
            (OUT/"ocr"/f"{vid_id}.json").write_text(json.dumps(
                [{"slide_text":"","confidence":0.0,"n_boxes":0}]*len(sents)))
        return

    total = len(vid_ids_with_video)
    t0 = time.time()
    for i, vid_id in enumerate(vid_ids_with_video):
        out_f = OUT/"ocr"/f"{vid_id}.json"
        if out_f.exists():
            log("T17-OCR", i+1, total, f"cached {vid_id}")
            continue
        sents = load_sents(vid_id)
        video = VID_DIR / f"{vid_id}.mp4"
        results = []
        tmp_dir = tempfile.mkdtemp()
        try:
            for seg in sents:
                ts = (seg.get("start",0) + seg.get("end", seg.get("start",0)+1)) / 2
                tmp_jpg = os.path.join(tmp_dir, "f.jpg")
                if not extract_frame(video, ts, tmp_jpg):
                    results.append({"slide_text":"","confidence":0.0,"n_boxes":0})
                    continue
                try:
                    res = ocr.ocr(tmp_jpg, cls=True)
                    lines = [l for blk in (res or []) for l in (blk or []) if l]
                    hi = [l for l in lines if l[1][1] > 0.5]
                    txt = " ".join(l[1][0] for l in hi).strip()
                    conf = float(np.mean([l[1][1] for l in hi])) if hi else 0.0
                    results.append({"slide_text":txt,"confidence":round(conf,4),"n_boxes":len(hi)})
                except Exception:
                    results.append({"slide_text":"","confidence":0.0,"n_boxes":0})
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        out_f.write_text(json.dumps(results, indent=2), encoding="utf-8")
        n_txt = sum(1 for r in results if r["slide_text"])
        log("T17-OCR", i+1, total, f"{vid_id} — {len(sents)} sents, {n_txt} with text")

    elapsed = time.time()-t0
    print(f"\n[T17-OCR ] Done — {len(list((OUT/'ocr').glob('*.json')))} files in {elapsed:.0f}s")


# ── T20: CLIP ─────────────────────────────────────────────────────────────────
def run_t20(vid_ids_with_video: list[str], no_media_ids: list[str]):
    print("\n" + "="*65)
    print("T20 — CLIP ViT-B/32 visual embeddings (GPU:1 / GPU:0)")
    print("="*65)

    # Handle no-media videos (zero embeddings + mask)
    for vid_id in no_media_ids:
        sents = load_sents(vid_id)
        n = max(1, len(sents))
        emb = np.zeros((n, 512), dtype=np.float32)
        np.save(str(OUT/"clip"/f"{vid_id}.npy"), emb)
        # Also save a mask file documenting missing data
        (OUT/"clip"/f"{vid_id}_mask.json").write_text(
            json.dumps({"no_media": True, "n_sents": n, "reason": "video not available"})
        )
        print(f"[T20-CLIP] {vid_id}: no media — zero embeddings ({n} sents)")

    try:
        import clip, torch
        from PIL import Image
        device = "cuda:1" if torch.cuda.device_count() > 1 else "cuda:0" if torch.cuda.is_available() else "cpu"
        model, preprocess = clip.load("ViT-B/32", device=device)
        model.eval()
        print(f"[T20-CLIP] CLIP ViT-B/32 loaded on {device}")
    except Exception as e:
        print(f"[T20-CLIP] FAILED: {e}")
        return

    import torch
    from PIL import Image
    BATCH = 32
    total = len(vid_ids_with_video)
    t0 = time.time()

    for i, vid_id in enumerate(vid_ids_with_video):
        out_f = OUT/"clip"/f"{vid_id}.npy"
        if out_f.exists():
            log("T20-CLIP", i+1, total, f"cached {vid_id}")
            continue
        sents = load_sents(vid_id)
        n = len(sents)
        embeddings = np.zeros((n, 512), dtype=np.float32)
        video = VID_DIR / f"{vid_id}.mp4"
        tmp_dir = tempfile.mkdtemp()
        try:
            frames, idxs = [], []
            for j, seg in enumerate(sents):
                ts = (seg.get("start",0) + seg.get("end", seg.get("start",0)+1)) / 2
                jpg = os.path.join(tmp_dir, f"f{j:05d}.jpg")
                if extract_frame(video, ts, jpg):
                    frames.append(jpg); idxs.append(j)
            for b in range(0, len(frames), BATCH):
                bf, bi = frames[b:b+BATCH], idxs[b:b+BATCH]
                imgs, oi = [], []
                for p, ix in zip(bf, bi):
                    try:
                        imgs.append(preprocess(Image.open(p).convert("RGB")))
                        oi.append(ix)
                    except Exception: pass
                if not imgs: continue
                t = torch.stack(imgs).to(device)
                with torch.no_grad():
                    f = model.encode_image(t)
                    f = f / f.norm(dim=-1, keepdim=True)  # L2 normalise
                    f = f.cpu().float().numpy()
                for feat, ix in zip(f, oi):
                    embeddings[ix] = feat
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        np.save(str(out_f), embeddings)
        n_ok = int(np.any(embeddings != 0, axis=1).sum())
        log("T20-CLIP", i+1, total, f"{vid_id} — {n_ok}/{n} encoded")

    elapsed = time.time()-t0
    print(f"\n[T20-CLIP] Done — {len(list((OUT/'clip').glob('*.npy')))} files in {elapsed:.0f}s")


# ── main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("="*65)
    print("  LECSEG — T17 OCR + T20 CLIP  (upload-verified batch mode)")
    try:
        import subprocess as sp
        gpus = sp.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],
                      capture_output=True, text=True).stdout.strip()
        print(f"  GPUs: {gpus}")
    except Exception: pass
    print("="*65)

    # Wait for all videos to finish uploading
    completed_ids = wait_for_uploads()

    # Separate IDs
    ids_with_video = sorted(completed_ids)
    ids_no_media   = sorted(NO_MEDIA)

    print(f"\n  Videos with media:    {len(ids_with_video)}")
    print(f"  Videos without media: {len(ids_no_media)} — {ids_no_media}")
    print(f"  (no-media videos get zero feature vectors + mask file)\n")

    # Run T17 and T20 in parallel threads (different GPUs)
    t17 = threading.Thread(target=run_t17, args=(ids_with_video, ids_no_media), daemon=False)
    t20 = threading.Thread(target=run_t20, args=(ids_with_video, ids_no_media), daemon=False)
    t17.start(); t20.start()
    t17.join(); t20.join()

    print("\n" + "="*65)
    print("ALL DONE")
    print(f"  OCR  : {len(list((OUT/'ocr').glob('*.json')))}/30 files")
    print(f"  CLIP : {len(list((OUT/'clip').glob('*.npy')))}/30 files")
    print(f"  No-media documented: {ids_no_media}")
    print("="*65)
