"""
Batch runner for T16/T17/T18/T20 preprocessing — parallel threads with top-level imports.
"""
from __future__ import annotations
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Import ALL modules at top level to avoid threading import deadlocks
from lecseg.preprocess.shot_detection import detect_and_save
from lecseg.preprocess.prosody import prosody_and_save
from lecseg.preprocess.ocr import ocr_and_save
from lecseg.features.visual_embeddings import embed_video

RAW_DIR     = ROOT / "data" / "raw"
TRANSCRIPTS = ROOT / "data" / "transcripts"
SENTENCES   = ROOT / "data" / "sentences"
SHOTS_DIR   = ROOT / "data" / "shots"
OCR_DIR     = ROOT / "data" / "ocr"
PROSODY_DIR = ROOT / "data" / "prosody"
VISUAL_DIR  = ROOT / "data" / "emb_visual"


def get_video_ids():
    manifest = ROOT / "data" / "manifest.jsonl"
    if manifest.exists():
        return [json.loads(l)["id"] for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [p.name for p in sorted(RAW_DIR.iterdir()) if p.is_dir() and not p.name.startswith(".")]


def run_shots(video_ids):
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    for vid in video_ids:
        out = SHOTS_DIR / f"{vid}_shots.json"
        if out.exists():
            done += 1
            continue
        vp = RAW_DIR / vid / "video.mp4"
        if not vp.exists():
            print(f"  T16 SKIP {vid}", flush=True)
            continue
        try:
            shots = detect_and_save(vp, out)
            print(f"  T16 {vid}: {len(shots)} shots", flush=True)
            done += 1
        except Exception as e:
            print(f"  T16 ERROR {vid}: {e}", flush=True)
    print(f"T16 DONE: {done}/{len(video_ids)}", flush=True)


def run_prosody(video_ids):
    PROSODY_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    for vid in video_ids:
        out = PROSODY_DIR / f"{vid}_prosody.npy"
        if out.exists():
            done += 1
            continue
        tp = TRANSCRIPTS / vid / "transcript.json"
        sp = SENTENCES / vid / "sentences.json"
        if not tp.exists() or not sp.exists():
            print(f"  T18 SKIP {vid}", flush=True)
            continue
        ap = RAW_DIR / vid / "audio.wav"
        if not ap.exists():
            ap = None
        try:
            feats = prosody_and_save(tp, sp, out, ap)
            print(f"  T18 {vid}: {feats.shape}", flush=True)
            done += 1
        except Exception as e:
            print(f"  T18 ERROR {vid}: {e}", flush=True)
    print(f"T18 DONE: {done}/{len(video_ids)}", flush=True)


def run_ocr(video_ids):
    OCR_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    for vid in video_ids:
        out = OCR_DIR / f"{vid}_ocr.json"
        if out.exists():
            done += 1
            continue
        vp = RAW_DIR / vid / "video.mp4"
        if not vp.exists():
            print(f"  T17 SKIP {vid}", flush=True)
            continue
        try:
            results = ocr_and_save(vp, out)
            print(f"  T17 {vid}: {len(results)} frames", flush=True)
            done += 1
        except Exception as e:
            print(f"  T17 ERROR {vid}: {e}", flush=True)
    print(f"T17 DONE: {done}/{len(video_ids)}", flush=True)


def run_visual(video_ids):
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    done = 0
    for vid in video_ids:
        out = VISUAL_DIR / f"{vid}.npy"
        if out.exists():
            done += 1
            continue
        vp = RAW_DIR / vid / "video.mp4"
        if not vp.exists():
            print(f"  T20 SKIP {vid}", flush=True)
            continue
        try:
            vecs, _ = embed_video(vp, out_path=out, fps=0.5)
            print(f"  T20 {vid}: {vecs.shape}", flush=True)
            done += 1
        except Exception as e:
            print(f"  T20 ERROR {vid}: {e}", flush=True)
    print(f"T20 DONE: {done}/{len(video_ids)}", flush=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", nargs="+", default=["all"],
                        choices=["shots", "ocr", "prosody", "visual", "all"])
    parser.add_argument("--sequential", action="store_true")
    args = parser.parse_args()
    tasks = set(args.tasks)
    run_all = "all" in tasks

    video_ids = get_video_ids()
    print(f"Processing {len(video_ids)} videos\n", flush=True)

    funcs = []
    if run_all or "shots"   in tasks: funcs.append(("T16-shots",   run_shots,   video_ids))
    if run_all or "prosody" in tasks: funcs.append(("T18-prosody", run_prosody, video_ids))
    if run_all or "ocr"     in tasks: funcs.append(("T17-ocr",     run_ocr,     video_ids))
    if run_all or "visual"  in tasks: funcs.append(("T20-visual",  run_visual,  video_ids))

    if args.sequential:
        for name, fn, ids in funcs:
            print(f"\n=== {name} ===", flush=True)
            fn(ids)
    else:
        threads = [threading.Thread(target=fn, args=(ids,), name=name, daemon=True)
                   for name, fn, ids in funcs]
        for t in threads:
            t.start()
            print(f"Started: {t.name}", flush=True)
        for t in threads:
            t.join()

    print("\nAll preprocessing complete.", flush=True)
