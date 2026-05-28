# LECSEG vast.ai Session — Context & Recovery Document

## Instance
- **IP:** 85.10.218.46  **Port:** 46035
- **GPU:** RTX 5060 Ti 16GB | Germany datacenter | $0.195/hr
- **Template:** PyTorch (Vast) CUDA 12.9
- **Repo on instance:** /workspace/lecseg/
- **State file:** /workspace/session_state.json
- **Master log:** /workspace/master.log

## Why we're here
Running T15–T21 (preprocessing pipeline) on GPU because local AMD RX 6600
has no CUDA. These tasks extract 4 modalities from 30 lecture videos:
- T15: sentence split (text units)
- T16: shot boundaries (TransNetV2, visual)
- T17: slide OCR (PaddleOCR, visual text)
- T18: prosody features (pauses + pitch, librosa)
- T19: text embeddings (MPNet 768-d)
- T20: CLIP visual embeddings (512-d)
- T21: align all modalities to sentence timeline

Without these, T29 ablation eval cannot run.

## Task dependency graph
```
T15 ──→ T19 ──┐
T16 ──→ T20 ──┤
T17 ──────────┤──→ T21 ──→ T29 (local)
T18 ──────────┘
```

## Recovery procedure (if session interrupted)

### Option A — Re-run master script (safest)
SSH into instance if still alive:
```bash
ssh -p 46035 root@85.10.218.46
bash /workspace/lecseg/scripts/vastai_run.sh 2>&1 | tee -a /workspace/master.log
```
The script reads session_state.json and skips completed tasks automatically.

### Option B — Instance destroyed, partial results
Download whatever completed:
```powershell
$HOST='85.10.218.46'; $PORT='46035'
# download each completed folder individually
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/sentences/ data/
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/shots/ data/
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/ocr/ data/
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/prosody/ data/
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/emb_text/ data/
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/emb_visual/ data/
scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/features/ data/
```
Then rent a new instance and re-run only remaining tasks.

### Option C — Resume with new Claude session
Paste this prompt to resume:
```
I am running LECSEG preprocessing on vast.ai instance 85.10.218.46:46035
(RTX 5060 Ti 16GB, Germany). The script /workspace/lecseg/scripts/vastai_run.sh
is the master script. Check /workspace/session_state.json for what has completed.
Tasks: T15 (sentence split), T16 (TransNetV2), T17 (PaddleOCR), T18 (prosody),
T19 (MPNet embeddings), T20 (CLIP), T21 (alignment). Dependency: T15 before T19,
T16 before T20, all before T21. Data is in /workspace/lecseg/data/.
Local machine: Windows 11, AMD RX 6600, project at G:\THESIS\PreThesis2_TopicSegmentation.
T12 autoannotation is running locally with mistral:7b (progress unknown — check
data/gt_hier/ file count). Help me resume from where we left off.
```

## What to do AFTER downloading results
1. Destroy vast.ai instance (stop billing)
2. Verify counts: each of sentences/shots/ocr/prosody/emb_text/emb_visual/features = 30 files
3. Wait for local T12 to finish (check: `ls data/gt_hier/*.json | wc -l` → 30)
4. Run T13 IAA: `.venv\Scripts\python.exe scripts/compute_iaa.py --tolerance 1 --verbose`
5. Run T29 ablation: `.venv\Scripts\python.exe scripts/run_eval.py --verbose`
6. Generate tables: `.venv\Scripts\python.exe scripts/tables.py results/eval.json`
7. Fill \todo{} numbers in paper/ieee.tex and thesis chapters

## Progress tracker (update manually)
| Task | Status | Files | Notes |
|------|--------|-------|-------|
| T15 sentence split | ⬜ | 0/30 | |
| T16 shot detection | ⬜ | 0/30 | |
| T17 OCR | ⬜ | 0/30 | |
| T18 prosody | ⬜ | 0/30 | |
| T19 text embeddings | ⬜ | 0/30 | |
| T20 visual embeddings | ⬜ | 0/30 | |
| T21 alignment | ⬜ | 0/30 | |
| T12 autoannotate (local) | 🔄 | 7/30 | mistral:7b running |
| T13 IAA (local) | ⬜ | blocked on T12 | |
| T29 ablation (local) | ⬜ | blocked on T21 | |
