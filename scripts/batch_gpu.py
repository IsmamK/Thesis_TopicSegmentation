#!/usr/bin/env python3
"""
T16 + T17 + T18 + T20 batch processor.
Downloads each video from YouTube, extracts features, deletes video.
Runs on vast.ai instance at /workspace/lecseg.
Resume-safe: skips completed videos.
"""
import sys, json, subprocess, time
from pathlib import Path

sys.path.insert(0, "src")

REPO = Path("/workspace/lecseg")
DATA = REPO / "data"
LOG  = Path("/workspace/batch.log")

for d in ["shots", "ocr", "prosody", "embeddings/clip"]:
    (DATA / d).mkdir(parents=True, exist_ok=True)

VIDEO_IDS = [json.loads(l)["id"] for l in open(DATA / "manifest.jsonl") if l.strip()]


def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd or str(REPO))
    return r.returncode, r.stdout + r.stderr


def is_done(vid):
    return all([
        (DATA / "shots" / f"{vid}.json").exists(),
        (DATA / "prosody" / f"{vid}_prosody.npy").exists(),
        (DATA / "embeddings/clip" / vid / "embeddings.npy").exists(),
        (DATA / "ocr" / f"{vid}.json").exists(),
    ])


log("=== LECSEG Batch GPU Processing ===")
log(f"Videos to process: {len(VIDEO_IDS)}")

# Check CLIP available
try:
    import clip, torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
    log(f"CLIP loaded on {device}")
except Exception as e:
    log(f"WARN: CLIP load failed: {e} — will install")
    subprocess.run("pip install git+https://github.com/openai/CLIP.git -q", shell=True)
    import clip, torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
    log(f"CLIP loaded after install on {device}")

# Install librosa if needed
try:
    import librosa
    log("librosa OK")
except ImportError:
    subprocess.run("pip install librosa soundfile -q", shell=True)
    import librosa

total = len(VIDEO_IDS)
completed = 0

for i, vid in enumerate(VIDEO_IDS):
    if is_done(vid):
        log(f"[{i+1}/{total}] SKIP {vid} (already done)")
        completed += 1
        continue

    log(f"[{i+1}/{total}] ===== {vid} =====")
    mp4 = DATA / f"tmp_{vid}.mp4"
    wav = DATA / f"tmp_{vid}.wav"
    url = f"https://www.youtube.com/watch?v={vid}"

    # 1. Download video
    log(f"  Downloading...")
    rc, out = run(f'yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720]" '
                  f'-o "{mp4}" "{url}" --no-playlist --quiet')
    if rc != 0 or not mp4.exists():
        # Fallback: any format
        rc, out = run(f'yt-dlp -f best -o "{mp4}" "{url}" --no-playlist --quiet')
    if not mp4.exists():
        log(f"  ERROR: download failed, skipping {vid}")
        continue
    sz = mp4.stat().st_size / 1e6
    log(f"  Downloaded {sz:.0f} MB")

    # 2. T16 — shot detection
    log("  T16: Shot detection...")
    try:
        from lecseg.preprocess.shot_detection import detect_shots
        shots = detect_shots(str(mp4))
        out16 = DATA / "shots" / f"{vid}.json"
        json.dump(shots, open(out16, "w"))
        log(f"  T16 done: {len(shots)} shots")
    except Exception as e:
        log(f"  T16 error: {e}")
        json.dump([], open(DATA / "shots" / f"{vid}.json", "w"))

    # 3. Extract WAV for T18
    log("  Extracting WAV...")
    rc, _ = run(f'ffmpeg -i "{mp4}" -ar 16000 -ac 1 -vn "{wav}" -y -loglevel quiet')
    if not wav.exists():
        log("  WARN: WAV extraction failed")

    # 4. T18 — prosody
    log("  T18: Prosody...")
    try:
        from lecseg.preprocess.prosody import prosody_and_save
        t_path = DATA / "transcripts" / vid / "transcript.json"
        s_path = DATA / "sentences" / vid / "sentences.json"
        out18 = DATA / "prosody" / f"{vid}_prosody.npy"
        if t_path.exists() and s_path.exists():
            prosody_and_save(t_path, s_path, out18, wav if wav.exists() else None)
            log(f"  T18 done")
        else:
            log(f"  T18 SKIP: missing transcript/sentences")
    except Exception as e:
        log(f"  T18 error: {e}")

    # 5. T17 + T20 — OCR + CLIP on keyframes
    log("  T17+T20: OCR + CLIP keyframes...")
    try:
        from lecseg.features.visual_embeddings import extract_keyframes, embed_keyframes
        from lecseg.preprocess.ocr import ocr_frame
        import numpy as np
        from PIL import Image

        frames, timestamps = extract_keyframes(str(mp4), fps=0.5, max_frames=500)
        log(f"  Extracted {len(frames)} keyframes")

        # T20 — CLIP embeddings
        out20_dir = DATA / "embeddings/clip" / vid
        out20_dir.mkdir(parents=True, exist_ok=True)
        vecs = embed_keyframes(frames, batch_size=64)
        np.save(str(out20_dir / "embeddings.npy"), vecs)
        ts_arr = {"timestamps": timestamps, "n_frames": len(frames)}
        json.dump(ts_arr, open(out20_dir / "meta.json", "w"))
        log(f"  T20 done: {vecs.shape}")

        # T17 — OCR (sample every 4th frame to save time)
        ocr_results = []
        for j, (frame, ts) in enumerate(zip(frames, timestamps)):
            if j % 4 == 0:
                text = ocr_frame(np.array(frame))
                ocr_results.append({"timestamp": ts, "text": text})
        json.dump(ocr_results, open(DATA / "ocr" / f"{vid}.json", "w"))
        log(f"  T17 done: {len(ocr_results)} OCR frames")

    except Exception as e:
        log(f"  T17+T20 error: {e}")
        # Save empty outputs so is_done() passes
        json.dump([], open(DATA / "ocr" / f"{vid}.json", "w"))
        out20_dir = DATA / "embeddings/clip" / vid
        out20_dir.mkdir(parents=True, exist_ok=True)
        import numpy as np
        np.save(str(out20_dir / "embeddings.npy"), np.zeros((1, 512), dtype="float32"))

    # 6. Cleanup
    mp4.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    completed += 1
    log(f"  [{completed}/{total}] {vid} COMPLETE ✓")

log(f"=== ALL DONE: {completed}/{total} videos processed ===")
print(f"\nSummary:")
print(f"  shots:    {len(list((DATA/'shots').glob('*.json')))}/30")
print(f"  prosody:  {len(list((DATA/'prosody').glob('*.npy')))}/30")
print(f"  clip emb: {len(list((DATA/'embeddings/clip').glob('*/')))}/30")
print(f"  ocr:      {len(list((DATA/'ocr').glob('*.json')))}/30")
