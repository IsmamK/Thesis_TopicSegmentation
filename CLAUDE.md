# LECSEG — Lecture Topic Segmentation

Pre-thesis project (T2520718). Python 3.14 on Windows.

## Environment

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Run tests
.\.venv\Scripts\python.exe -m pytest tests\ -q

# Run full pipeline
.\.venv\Scripts\python.exe scripts/pipeline.py --verbose

# Run demo
streamlit run scripts/demo.py
```

## Project layout

```
src/lecseg/
  metrics.py              T22: Pk, WD, BS, F1, H-WD
  baselines/
    classical.py          T23: TextTiling, C99
    neural.py             T24: CosineSeg, KMeansSeg, BertSeg
  preprocess/
    sentence_split.py     T15: Whisper segment -> sentences (spaCy)
    shot_detection.py     T16: TransNetV2 / fallback shot boundaries
    ocr.py                T17: PaddleOCR slide text extraction
    prosody.py            T18: Pause duration + pitch (librosa)
  features/
    text_embeddings.py    T19: SBERT/MPNet/E5/BGE embeddings
    alignment.py          T21: Align modalities to sentence timeline
  models/
    fusion.py             T25/N2: Reliability-weighted fusion
    boundary_predictor.py T26/N1: Two-stage boundary predictor
    hierarchical.py       T27/N3: Chapter + subtopic hierarchy
  refine/
    llm_refine.py         T28/N4: Ollama LLM refinement + titling
  eval/
    stats.py              T30: Bootstrap CIs + Wilcoxon tests
    error_analysis.py     T31: FP/FN/near-miss analysis

scripts/
  pipeline.py             End-to-end pipeline (all videos)
  run_eval.py             T29: Full ablation battery
  compute_iaa.py          T13: Cohen's kappa IAA
  annotate.py             T12: Streamlit annotation tool
  autoannotate.py         LLM draft annotations (Ollama)
  demo.py                 T39: Streamlit web demo
  vast_transcribe.py      T14: Whisper on vast.ai GPU
  tables.py               LaTeX table generation from eval results
  figures.py              Thesis figures (matplotlib)
  check_transcripts.py    Verify downloaded transcripts
  download_transcripts.py SCP transcripts from vast.ai
```

## Data layout

```
data/
  transcripts/<id>/transcript.json   Whisper output (T14)
  sentences/<id>/sentences.json      Sentence split (T15)
  embeddings/<model>/<id>/embeddings.npy  Text vectors (T19)
  gt/<id>.json                       Chapter GT from YouTube
  gt_hier/<id>.json                  Hierarchical annotation (T12)
  gt_hier/double/<id>.json           Second-annotator copy (T13)
  predictions/<id>.json              Model predictions
  results/eval.json                  Evaluation results (T29)
```

## vast.ai transcription

Instance: 154.12.38.116 port 21115 (RTX 5090, ~$0.67/hr)

```bash
# Check progress
ssh -o StrictHostKeyChecking=no -i $env:USERPROFILE\.ssh\id_rsa -p 21115 root@154.12.38.116 \
  "ls /workspace/transcripts/ | wc -l && tail -4 /workspace/transcribe.log"

# Download when done (30/30)
scp -P 21115 -r root@154.12.38.116:/workspace/transcripts/ data/transcripts/
```

After download: **DESTROY the instance immediately** to stop billing.

## Novel method summary (N1–N4)

- **N1** (T26): Two-stage predictor — broad candidates via cosine drops, then refine
- **N2** (T25): Reliability-weighted fusion — weight modalities by inverse entropy
- **N3** (T27): Hierarchical output — chapters ⊂ subtopics
- **N4** (T28): LLM refinement + titling — Ollama llama3.1:8b

## Key commands

```powershell
# After transcripts downloaded, run sentence splitting
.\.venv\Scripts\python.exe src/lecseg/preprocess/sentence_split.py

# Or full pipeline
.\.venv\Scripts\python.exe scripts/pipeline.py --model mpnet --verbose

# Eval after annotation
.\.venv\Scripts\python.exe scripts/run_eval.py --verbose

# IAA report
.\.venv\Scripts\python.exe scripts/compute_iaa.py --tolerance 1 --verbose
```

## Test status

177 tests passing as of 2026-05-26.
Tasks done: 29/47 (62%) as of 2026-05-26 (3 in progress, transcription ongoing).

## Post-transcription workflow

```powershell
# 1. Download from vast.ai (run when 30/30 done)
python scripts/download_transcripts.py
# IMMEDIATELY destroy vast.ai instance after download!

# 2. Verify transcripts
python scripts/check_transcripts.py

# 3. Sentence splitting
.venv\Scripts\python src/lecseg/preprocess/sentence_split.py

# 4. Auto-annotate (Ollama must be running)
python scripts/autoannotate.py

# 5. Review annotations
streamlit run scripts/annotate.py

# 6. IAA
python scripts/compute_iaa.py --verbose

# 7. Full pipeline
python scripts/pipeline.py --model mpnet --verbose

# 8. Ablation eval
python scripts/run_eval.py --verbose

# 9. Generate tables + figures
python scripts/tables.py results/eval.json
python scripts/figures.py results/eval.json --output figures/
```
