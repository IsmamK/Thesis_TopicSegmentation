"""Verify T01-T31 deliverables are present in expected locations."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC  = ROOT / "src" / "lecseg"
RESULTS = ROOT / "results"

def check(name, condition, detail=""):
    sym = "OK  " if condition else "FAIL"
    print(f"  [{sym}] {name}" + (f" -- {detail}" if detail else ""))
    return condition

def count(path, pattern):
    p = Path(path)
    return len(list(p.glob(pattern))) if p.exists() else 0

def kb(path):
    p = Path(path)
    return f"{round(p.stat().st_size/1024,1)}KB" if p.exists() else "MISSING"

results = {}

print("-- T01-T11: Setup & Dataset --")
results["T01"] = check("T01 repo structure",    (SRC/"__init__.py").exists())
results["T02"] = check("T02 pyproject.toml",    (ROOT/"pyproject.toml").exists())
results["T03"] = check("T03 videos in raw/",    count(DATA/"raw","*/video.mp4") >= 28,
                        f"{count(DATA/'raw','*/video.mp4')}/30 mp4s")
results["T04"] = check("T04 gt/*.json",         count(DATA/"gt","*.json") >= 28,
                        f"{count(DATA/'gt','*.json')}/30")
results["T05"] = check("T05 gt_hier/*.json",    count(DATA/"gt_hier","*.json") >= 28,
                        f"{count(DATA/'gt_hier','*.json')}/30 (excl iaa_report)")
results["T06"] = check("T06 double annots",     count(DATA/"gt_hier"/"double","*.json") >= 28,
                        f"{count(DATA/'gt_hier'/'double','*.json')}/30")
results["T07"] = check("T07 metrics.py",        (SRC/"metrics.py").exists())
results["T08"] = check("T08 classical.py",      (SRC/"baselines"/"classical.py").exists())
results["T09"] = check("T09 neural.py",         (SRC/"baselines"/"neural.py").exists())
results["T10"] = check("T10 sentence_split.py", (SRC/"preprocess"/"sentence_split.py").exists())
results["T11"] = check("T11 sentences data",    count(DATA/"sentences","*/sentences.json") >= 28,
                        f"{count(DATA/'sentences','*/sentences.json')}/30")

print("\n-- T12-T14: Annotation & Transcription --")
results["T12"] = check("T12 annotate.py",       (ROOT/"scripts"/"annotate.py").exists())
results["T13"] = check("T13 iaa_report.json",   (DATA/"gt_hier"/"iaa_report.json").exists(),
                        kb(DATA/"gt_hier"/"iaa_report.json"))
results["T14"] = check("T14 transcripts",       count(DATA/"transcripts","*/transcript.json") >= 28,
                        f"{count(DATA/'transcripts','*/transcript.json')}/30")

print("\n-- T15-T20: Preprocessing & Features --")
results["T15"] = check("T15 sentences data",    count(DATA/"sentences","*/sentences.json") >= 28,
                        f"{count(DATA/'sentences','*/sentences.json')}/30")
results["T16"] = check("T16 shots data",        count(DATA/"shots","*_shots.json") >= 28,
                        f"{count(DATA/'shots','*_shots.json')}/30")
results["T17"] = check("T17 ocr data",          count(DATA/"ocr","*_ocr.json") >= 28,
                        f"{count(DATA/'ocr','*_ocr.json')}/30")
results["T18"] = check("T18 prosody data",      count(DATA/"prosody","*_prosody.npy") >= 28,
                        f"{count(DATA/'prosody','*_prosody.npy')}/30")
results["T19"] = check("T19 text embeddings",   count(DATA/"embeddings","**/*.npy") >= 28,
                        f"{count(DATA/'embeddings','**/*.npy')}/30")
results["T20"] = check("T20 CLIP embeddings",   count(DATA/"emb_visual"/"clip","*.npy") >= 28,
                        f"{count(DATA/'emb_visual'/'clip','*.npy')}/30")

print("\n-- T21-T28: Models --")
results["T21"] = check("T21 alignment.py",         (SRC/"features"/"alignment.py").exists())
results["T22"] = check("T22 metrics.py",            (SRC/"metrics.py").exists())
results["T23"] = check("T23 classical.py",          (SRC/"baselines"/"classical.py").exists())
results["T24"] = check("T24 neural.py",             (SRC/"baselines"/"neural.py").exists())
results["T25"] = check("T25 fusion.py",             (SRC/"models"/"fusion.py").exists())
results["T26"] = check("T26 boundary_predictor.py", (SRC/"models"/"boundary_predictor.py").exists())
results["T27"] = check("T27 hierarchical.py",       (SRC/"models"/"hierarchical.py").exists())
results["T28"] = check("T28 llm_refine.py",         (SRC/"refine"/"llm_refine.py").exists())

print("\n-- T29-T31: Evaluation --")
results["T29"] = check("T29 results/eval.json",          (RESULTS/"eval.json").exists(),
                        kb(RESULTS/"eval.json"))
results["T30"] = check("T30 results/stats.json",         (RESULTS/"stats.json").exists(),
                        kb(RESULTS/"stats.json"))
results["T31"] = check("T31 results/error_analysis.json",(RESULTS/"error_analysis.json").exists(),
                        kb(RESULTS/"error_analysis.json"))
results["T31p"]= check("T31 predictions/",               count(DATA/"predictions","*.json") >= 28,
                        f"{count(DATA/'predictions','*.json')}/30")

done = sum(1 for v in results.values() if v)
total = len(results)
print(f"\n{'='*55}")
print(f"TOTAL: {done}/{total} checks pass")
missing = [k for k, v in results.items() if not v]
if missing:
    print(f"FAILING: {missing}")
else:
    print("ALL DELIVERABLES PRESENT")
print("="*55)
