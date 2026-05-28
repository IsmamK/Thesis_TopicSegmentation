"""
Auto-download all outputs from vast.ai then verify T1-T31 deliverables.
Run after OCR completes: python scripts/verify_and_download.py
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
DATA  = ROOT / "data"
SRC   = ROOT / "src" / "lecseg"

SSH   = ["ssh", "-o", "StrictHostKeyChecking=no", "-p", "24993", "root@154.42.3.36"]
SCP   = ["scp", "-o", "StrictHostKeyChecking=no", "-P", "24993"]

VIDEO_IDS = [
    "7K1sB05pE0A","8yT4RZy1t3s","9N1MxkbFhsc","AMl6E4cLrwE","D8RRq3TbtHU",
    "fsLh-NYhOoU","GR63MMAi-fs","HtSuA80QTyo","Hy7ou5R_vjE","j0wJBEZdwLs",
    "jGwO_UgTS7I","JP7ITIXGpHk","KlVHqq38KJU","KNwMiydCYA4","KOKnWaLiL8w",
    "lUUte2o2Sn8","MGyygiXMzRk","NK-BxowMIfg","NNnIGh9g6fA","Ns6GB4Dph9U",
    "oOya3cFmAMc","oqRU2So6Z2Y","Qw4l1w0rkjs","Rl0ludWTLxs","S7TUe5w6RHo",
    "TjZBTDzGeGg","uK2eFv7ne_Q","uO5k9xcD1gU","YdOXS_9_P4U","zNVQfWC_evg",
]

def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)

# ── Download ──────────────────────────────────────────────────────────────────
def download_all():
    print("\n=== DOWNLOADING FROM VAST.AI ===")
    targets = [
        ("/root/output/prosody/", str(DATA / "prosody") + "/"),
        ("/root/output/ocr/",     str(DATA / "ocr") + "/"),
        ("/root/output/clip/",    str(DATA / "emb_visual" / "clip") + "/"),
    ]
    for remote, local in targets:
        Path(local).mkdir(parents=True, exist_ok=True)
        cmd = SCP + ["-r", f"root@154.42.3.36:{remote}", local]
        r = run(cmd)
        n = len(list(Path(local).glob("*.*")))
        status = "✓" if r.returncode == 0 else "✗"
        print(f"  {status} {remote} → {local}  ({n} files)")

# ── Verify T1-T31 ─────────────────────────────────────────────────────────────
def check(name, condition, detail=""):
    sym = "✅" if condition else "❌"
    print(f"  {sym} {name}" + (f" — {detail}" if detail else ""))
    return condition

def count(path, pattern):
    p = Path(path)
    return len(list(p.glob(pattern))) if p.exists() else 0

def verify():
    print("\n=== T1-T31 DELIVERABLE VERIFICATION ===\n")
    results = {}

    # T1-T11: Setup & dataset (code/config based)
    print("── T1-T11: Setup & Dataset ──")
    results["T01"] = check("T01 repo structure", (ROOT/"src"/"lecseg"/"__init__.py").exists())
    results["T02"] = check("T02 venv/pyproject", (ROOT/"pyproject.toml").exists())
    results["T03"] = check("T03 video list", (DATA/"video_list.csv").exists(),
                           f"{len(list((DATA/'raw').glob('*/video.mp4')))} videos in raw/")
    results["T04"] = check("T04 gt annotations", count(DATA/"gt","*.json") >= 25,
                           f"{count(DATA/'gt','*.json')}/30 GT files")
    results["T05"] = check("T05 gt_hier annotations", count(DATA/"gt_hier","*.json") >= 10,
                           f"{count(DATA/'gt_hier','*.json')} hier GT files")
    results["T06"] = check("T06 double annotations (IAA)", count(DATA/"gt_hier"/"double","*.json") >= 5,
                           f"{count(DATA/'gt_hier'/'double','*.json')} double files")
    results["T07"] = check("T07 metrics code", (SRC/"metrics.py").exists())
    results["T08"] = check("T08 baselines/classical", (SRC/"baselines"/"classical.py").exists())
    results["T09"] = check("T09 baselines/neural", (SRC/"baselines"/"neural.py").exists())
    results["T10"] = check("T10 sentence splitting code", (SRC/"preprocess"/"sentence_split.py").exists())
    results["T11"] = check("T11 sentences data", count(DATA/"sentences","*/sentences.json") >= 28,
                           f"{count(DATA/'sentences','*/sentences.json')}/30 videos split")

    print("\n── T12-T14: Annotation & Transcription ──")
    results["T12"] = check("T12 annotate script", (ROOT/"scripts"/"annotate.py").exists())
    results["T13"] = check("T13 IAA script", (ROOT/"scripts"/"compute_iaa.py").exists())
    results["T14"] = check("T14 transcripts", count(DATA/"transcripts","*/transcript.json") >= 28,
                           f"{count(DATA/'transcripts','*/transcript.json')}/30 transcripts")

    print("\n── T15-T20: Feature Extraction ──")
    results["T15"] = check("T15 sentence_split code", (SRC/"preprocess"/"sentence_split.py").exists())
    results["T16"] = check("T16 shot detection data", count(DATA/"shots","*.json") >= 25,
                           f"{count(DATA/'shots','*.json')} shot files")
    results["T17"] = check("T17 OCR data", count(DATA/"ocr","*.json") >= 28,
                           f"{count(DATA/'ocr','*.json')}/30 OCR files")
    results["T18"] = check("T18 prosody data", count(DATA/"prosody","*.json") >= 28,
                           f"{count(DATA/'prosody','*.json')}/30 prosody files")

    # T19: text embeddings
    emb_dir = DATA / "embeddings"
    emb_count = count(emb_dir, "**/*.npy")
    results["T19"] = check("T19 text embeddings", emb_count >= 28,
                           f"{emb_count} embedding files in data/embeddings/")

    results["T20"] = check("T20 CLIP visual embeddings",
                           count(DATA/"emb_visual"/"clip","*.npy") >= 28,
                           f"{count(DATA/'emb_visual'/'clip','*.npy')}/30 CLIP files")

    print("\n── T21-T28: Models ──")
    results["T21"] = check("T21 alignment code", (SRC/"features"/"alignment.py").exists())
    results["T22"] = check("T22 metrics code", (SRC/"metrics.py").exists())
    results["T23"] = check("T23 classical baselines", (SRC/"baselines"/"classical.py").exists())
    results["T24"] = check("T24 neural baselines", (SRC/"baselines"/"neural.py").exists())
    results["T25"] = check("T25/N2 fusion model", (SRC/"models"/"fusion.py").exists())
    results["T26"] = check("T26/N1 boundary predictor", (SRC/"models"/"boundary_predictor.py").exists())
    results["T27"] = check("T27/N3 hierarchical model", (SRC/"models"/"hierarchical.py").exists())
    results["T28"] = check("T28/N4 LLM refine", (SRC/"refine"/"llm_refine.py").exists())

    print("\n── T29-T31: Evaluation ──")
    results["T29"] = check("T29 eval script", (ROOT/"scripts"/"run_eval.py").exists())
    eval_json = DATA / "results" / "eval.json"
    results["T30"] = check("T30 eval results", eval_json.exists(),
                           f"{'exists' if eval_json.exists() else 'MISSING — run scripts/run_eval.py'}")
    results["T31"] = check("T31 error analysis code", (SRC/"eval"/"error_analysis.py").exists())

    # Summary
    done = sum(results.values())
    total = len(results)
    print(f"\n{'='*50}")
    print(f"TOTAL: {done}/{total} tasks have deliverables present")
    missing = [k for k, v in results.items() if not v]
    if missing:
        print(f"MISSING: {missing}")
    else:
        print("ALL DELIVERABLES PRESENT ✅")
    print('='*50)
    return results

if __name__ == "__main__":
    download_all()
    verify()
