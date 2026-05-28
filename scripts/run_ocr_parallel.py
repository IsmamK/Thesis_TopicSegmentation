"""
T17 OCR — parallel execution across 2 GPUs.
Strategy:
  1. Extract frames for ALL videos in parallel (CPU ThreadPool, ffmpeg fps filter)
  2. Split videos across 2 EasyOCR workers (GPU:0 and GPU:1)
  3. Each worker processes its videos sequentially (EasyOCR not thread-safe)

Sparse sampling: 1 frame/30s → covers all slide transitions.
~4 min/video × 30 videos / 2 GPUs = ~60 min total.
"""
from __future__ import annotations
import json, multiprocessing, os, shutil, subprocess, sys, tempfile, threading, time
from pathlib import Path
import numpy as np

ROOT     = Path("/root/data")
VID_DIR  = Path("/root/videos")
OUT      = Path("/root/output/ocr")
SENT_DIR = ROOT / "sentences"
OUT.mkdir(parents=True, exist_ok=True)

NO_MEDIA = {"jGwO_UgTS7I", "lUUte2o2Sn8", "NK-BxowMIfg"}
ALL_VIDEO_IDS = [p.stem for p in sorted(VID_DIR.glob("*.mp4"))]
ALL_IDS = ALL_VIDEO_IDS + sorted(NO_MEDIA)  # 30 total

T0 = time.time()
_lock = threading.Lock()
_done = 0

def ts(): return f"{time.time()-T0:.0f}s"

def log(msg):
    print(f"[OCR {ts()}] {msg}", flush=True)

def load_sents(vid_id):
    f = SENT_DIR / vid_id / "sentences.json"
    raw = json.loads(f.read_text())
    return raw["sentences"] if isinstance(raw, dict) else raw

def extract_frames_batch(vid_id, tmp_dir) -> list[float]:
    """Extract 1 frame/30s for entire video. Returns list of timestamps."""
    video = VID_DIR / f"{vid_id}.mp4"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(video),
         "-vf", "fps=1/30,scale=1280:-1",
         "-q:v", "2", os.path.join(tmp_dir, "f%05d.jpg")],
        capture_output=True, timeout=600
    )
    frames = sorted(f for f in os.listdir(tmp_dir) if f.endswith(".jpg"))
    timestamps = [i * 30 for i in range(len(frames))]
    return timestamps

def assign_ocr_to_sentences(sents, frame_texts, frame_timestamps):
    results = []
    for seg in sents:
        ts_ = (seg.get("start", 0) + seg.get("end", seg.get("start", 0) + 1)) / 2
        if not frame_timestamps:
            results.append({"slide_text": "", "confidence": 0.0, "n_boxes": 0})
            continue
        idx = min(range(len(frame_timestamps)), key=lambda i: abs(frame_timestamps[i] - ts_))
        ft = frame_texts[idx]
        results.append({"slide_text": ft["text"], "confidence": ft["conf"], "n_boxes": ft["n"]})
    return results

def ocr_worker(gpu_id: int, video_ids: list[str]):
    """One EasyOCR worker per GPU. Processes its assigned videos."""
    global _done
    import easyocr
    log(f"GPU:{gpu_id} worker starting — {len(video_ids)} videos")
    reader = easyocr.Reader(["en"], gpu=True, gpu_memory=0.4 if gpu_id == 0 else 0.4,
                             verbose=False)
    log(f"GPU:{gpu_id} EasyOCR loaded")

    for vid_id in video_ids:
        out_f = OUT / f"{vid_id}.json"
        sents = load_sents(vid_id)

        if vid_id in NO_MEDIA:
            out_f.write_text(json.dumps(
                [{"slide_text": "", "confidence": 0.0, "n_boxes": 0, "no_media": True}] * len(sents),
                indent=2))
            with _lock:
                _done += 1; d = _done
            log(f"GPU:{gpu_id} {d}/{len(ALL_IDS)} no-media {vid_id}")
            continue

        tmp = tempfile.mkdtemp()
        try:
            timestamps = extract_frames_batch(vid_id, tmp)
            frame_files = sorted(f for f in os.listdir(tmp) if f.endswith(".jpg"))
            frame_texts = []
            for ff in frame_files:
                try:
                    det = reader.readtext(os.path.join(tmp, ff), detail=1)
                    hi = [d for d in det if d[2] > 0.5]
                    txt = " ".join(d[1] for d in hi).strip()
                    conf = float(np.mean([d[2] for d in hi])) if hi else 0.0
                    frame_texts.append({"text": txt, "conf": round(conf, 4), "n": len(hi)})
                except Exception:
                    frame_texts.append({"text": "", "conf": 0.0, "n": 0})

            results = assign_ocr_to_sentences(sents, frame_texts, timestamps)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        out_f.write_text(json.dumps(results, indent=2), encoding="utf-8")
        n_txt = sum(1 for r in results if r["slide_text"])
        with _lock:
            _done += 1; d = _done
        log(f"GPU:{gpu_id} {d}/{len(ALL_IDS)} {vid_id} — {len(frame_files)} frames, {n_txt}/{len(sents)} with text")

    log(f"GPU:{gpu_id} worker DONE")


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)

    # Write no-media placeholders immediately
    for vid_id in sorted(NO_MEDIA):
        out_f = OUT / f"{vid_id}.json"
        sents = load_sents(vid_id)
        out_f.write_text(json.dumps(
            [{"slide_text": "", "confidence": 0.0, "n_boxes": 0, "no_media": True}] * len(sents),
            indent=2))
    log(f"3 no-media placeholders written")

    # Split videos across 2 GPUs — interleave so big/small videos balance
    ids_to_process = [v for v in ALL_VIDEO_IDS
                      if not (OUT / f"{v}.json").exists() or
                      json.loads((OUT / f"{v}.json").read_text())[0].get("slide_text") == "" and
                      not json.loads((OUT / f"{v}.json").read_text())[0].get("no_media")]

    log(f"Videos to process: {len(ids_to_process)}")
    gpu0_ids = ids_to_process[0::2]   # even indices → GPU:0
    gpu1_ids = ids_to_process[1::2]   # odd indices  → GPU:1

    log(f"GPU:0 → {len(gpu0_ids)} videos, GPU:1 → {len(gpu1_ids)} videos")

    # Set GPU env per process using subprocess
    import subprocess as sp
    env0 = os.environ.copy(); env0["CUDA_VISIBLE_DEVICES"] = "0"
    env1 = os.environ.copy(); env1["CUDA_VISIBLE_DEVICES"] = "1"

    # Use threads (each EasyOCR instance is isolated by CUDA_VISIBLE_DEVICES)
    def run_gpu(gpu_id, ids, env_gpu):
        ids_json = json.dumps(ids)
        code = f"""
import json, os, shutil, subprocess, tempfile, time, threading
from pathlib import Path
import numpy as np

OUT=Path('/root/output/ocr'); SENT_DIR=Path('/root/data/sentences')
VID_DIR=Path('/root/videos'); NO_MEDIA={{'jGwO_UgTS7I','lUUte2o2Sn8','NK-BxowMIfg'}}
T0=time.time()
IDS={repr(ids)}

def ts(): return f"{{time.time()-T0:.0f}}s"
def load_sents(v):
    f=SENT_DIR/v/'sentences.json'; raw=json.loads(f.read_text())
    return raw['sentences'] if isinstance(raw,dict) else raw

import easyocr
reader=easyocr.Reader(['en'], gpu=True, verbose=False)
print(f'[GPU:{gpu_id} {{ts()}}] EasyOCR ready, {{len(IDS)}} videos', flush=True)

for i,vid_id in enumerate(IDS):
    out_f=OUT/f'{{vid_id}}.json'
    sents=load_sents(vid_id)
    video=VID_DIR/f'{{vid_id}}.mp4'
    tmp=tempfile.mkdtemp()
    try:
        subprocess.run(['ffmpeg','-y','-i',str(video),'-vf','fps=1/30,scale=1280:-1',
            '-q:v','2',os.path.join(tmp,'f%05d.jpg')],capture_output=True,timeout=600)
        frames=sorted(f for f in os.listdir(tmp) if f.endswith('.jpg'))
        timestamps=[j*30 for j in range(len(frames))]
        frame_texts=[]
        for ff in frames:
            try:
                det=reader.readtext(os.path.join(tmp,ff),detail=1)
                hi=[d for d in det if d[2]>0.5]
                frame_texts.append({{'text':' '.join(d[1] for d in hi).strip(),'conf':round(float(np.mean([d[2] for d in hi])) if hi else 0.0,4),'n':len(hi)}})
            except: frame_texts.append({{'text':'','conf':0.0,'n':0}})
        results=[]
        for seg in sents:
            ts_=(seg.get('start',0)+seg.get('end',seg.get('start',0)+1))/2
            idx=min(range(len(timestamps)),key=lambda k:abs(timestamps[k]-ts_)) if timestamps else 0
            ft=frame_texts[idx] if frame_texts else {{'text':'','conf':0.0,'n':0}}
            results.append({{'slide_text':ft['text'],'confidence':ft['conf'],'n_boxes':ft['n']}})
    finally: shutil.rmtree(tmp,ignore_errors=True)
    out_f.write_text(json.dumps(results,indent=2),encoding='utf-8')
    n_txt=sum(1 for r in results if r['slide_text'])
    print(f'[GPU:{gpu_id} {{ts()}}] {{i+1}}/{{len(IDS)}} {{vid_id}} — {{len(frames)}} frames, {{n_txt}}/{{len(sents)}} with text',flush=True)
print(f'[GPU:{gpu_id} {{ts()}}] ALL DONE',flush=True)
"""
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        r = subprocess.run(
            ["/venv/main/bin/python3", "-c", code],
            env=env
        )

    t0 = threading.Thread(target=run_gpu, args=(0, gpu0_ids, env0), daemon=False)
    t1 = threading.Thread(target=run_gpu, args=(1, gpu1_ids, env1), daemon=False)
    t0.start(); t1.start()
    t0.join(); t1.join()

    total = len(list(OUT.glob("*.json")))
    log(f"=== ALL OCR DONE — {total}/30 files ===")
