"""
T18 prosody runner — uses concurrent.futures with spawn context to avoid fork deadlocks.
Each worker processes one video: load full audio, then PYIN per sentence chunk.
"""
from __future__ import annotations
import json, os, sys, time, threading
from pathlib import Path
import concurrent.futures as cf

ROOT = Path("/root/data")
OUT = Path("/root/output")
OUT.mkdir(exist_ok=True)
(OUT / "prosody").mkdir(exist_ok=True)
(OUT / "ocr").mkdir(exist_ok=True)
(OUT / "clip").mkdir(exist_ok=True)

SENTENCES_DIR = ROOT / "sentences"
MP3_DIR = ROOT / "mp3"


# ── progress ───────────────────────────────────────────────────────────────────
_lock = threading.Lock()
_done = 0
_total = 0
_start = time.time()

def _tick(vid_id: str, ok: bool):
    global _done
    with _lock:
        _done += 1
        d, t = _done, _total
    elapsed = time.time() - _start
    eta = (elapsed / d * (t - d)) if d > 0 else 0
    bar = "█" * int(d/t*30) + "░" * (30 - int(d/t*30)) if t else ""
    eta_s = f"{int(eta//60)}m{int(eta%60)}s"
    status = "ok" if ok else "ERR"
    print(f"[T18-PRO] [{bar}] {d:2d}/{t}  ETA {eta_s}  {status} {vid_id}", flush=True)


# ── per-video worker (runs in subprocess) ─────────────────────────────────────
def _process_video(args: tuple) -> tuple[str, bool, str]:
    vid_id, mp3_path, sentences_path, out_path = args
    try:
        import librosa, numpy as np

        raw = json.loads(Path(sentences_path).read_text())
        sents = raw["sentences"] if isinstance(raw, dict) else raw
        if not sents:
            Path(out_path).write_text(json.dumps([]))
            return vid_id, True, ""

        y, sr = librosa.load(str(mp3_path), sr=22050, mono=True)
        results = []
        for i, seg in enumerate(sents):
            start = seg.get("start", 0)
            end = seg.get("end", start + 1)
            s0 = int(start * sr)
            s1 = int(end * sr)
            chunk = y[s0:s1]
            if len(chunk) < int(sr * 0.05):
                results.append({"pause_after": 0.0, "mean_pitch": 0.0, "pitch_std": 0.0})
                continue
            try:
                f0, _, _ = librosa.pyin(chunk, fmin=50, fmax=400, sr=sr)
                valid = f0[~np.isnan(f0)] if f0 is not None else np.array([])
                mean_p = float(np.mean(valid)) if len(valid) else 0.0
                std_p = float(np.std(valid)) if len(valid) else 0.0
            except Exception:
                mean_p = std_p = 0.0
            pause = max(0.0, sents[i+1].get("start", end) - end) if i + 1 < len(sents) else 0.0
            results.append({"pause_after": pause, "mean_pitch": mean_p, "pitch_std": std_p})

        Path(out_path).write_text(json.dumps(results, indent=2))
        return vid_id, True, ""
    except Exception as e:
        return vid_id, False, str(e)[:120]


# ── T17/T20 placeholders (no videos) ──────────────────────────────────────────
def write_placeholders():
    import numpy as np
    n_ocr = n_clip = 0
    for sent_dir in sorted(SENTENCES_DIR.iterdir()):
        vid_id = sent_dir.name
        sent_f = sent_dir / "sentences.json"
        if not sent_f.exists():
            continue
        raw = json.loads(sent_f.read_text())
        sents = raw["sentences"] if isinstance(raw, dict) else raw
        n = len(sents)

        ocr_f = OUT / "ocr" / f"{vid_id}.json"
        if not ocr_f.exists():
            ocr_f.write_text(json.dumps([{"slide_text": "", "confidence": 0.0}] * n))
            n_ocr += 1

        clip_f = OUT / "clip" / f"{vid_id}.npy"
        if not clip_f.exists():
            np.save(str(clip_f), np.zeros((n, 512), dtype=np.float32))
            n_clip += 1

    print(f"[T17-OCR]  wrote {n_ocr} placeholder files")
    print(f"[T20-CLIP] wrote {n_clip} placeholder files")


# ── main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.set_start_method("spawn", force=True)

    print("=== LECSEG Remote Task Runner ===")
    print(f"CPUs available: {os.cpu_count()}")

    # T17/T20 placeholders (fast)
    write_placeholders()

    # Build T18 jobs
    jobs = []
    for mp3 in sorted(MP3_DIR.glob("*.mp3")):
        vid_id = mp3.stem
        sent_f = SENTENCES_DIR / vid_id / "sentences.json"
        out_f = OUT / "prosody" / f"{vid_id}.json"
        if sent_f.exists() and not out_f.exists():
            jobs.append((vid_id, str(mp3), str(sent_f), str(out_f)))

    _total = len(jobs)
    print(f"\n[T18-PRO] Starting {_total} videos with 8 workers (spawn)")
    print(f"[T18-PRO] Each worker loads full audio + runs PYIN per sentence\n")
    _start = time.time()

    with cf.ProcessPoolExecutor(max_workers=8) as pool:
        futs = {pool.submit(_process_video, j): j[0] for j in jobs}
        for fut in cf.as_completed(futs):
            vid_id, ok, err = fut.result()
            _tick(vid_id, ok)
            if not ok:
                print(f"  ERROR {vid_id}: {err}", flush=True)

    elapsed = time.time() - _start
    n_done = len(list((OUT / "prosody").glob("*.json")))
    print(f"\n=== T18 DONE in {elapsed:.0f}s — {n_done} files written ===")
    print(f"OCR:  {len(list((OUT/'ocr').glob('*.json')))} files")
    print(f"CLIP: {len(list((OUT/'clip').glob('*.npy')))} files")
