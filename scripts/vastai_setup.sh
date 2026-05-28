#!/usr/bin/env bash
# =============================================================================
#  LECSEG — vast.ai GPU setup + full preprocessing run
#  Template: PyTorch (Vast)  |  Instance: RTX 5060 Ti 16GB (#34204366 Germany)
#
#  USAGE (paste into SSH session after instance boots):
#    bash vastai_setup.sh 2>&1 | tee /workspace/run.log
# =============================================================================
set -euo pipefail
WORKSPACE=/workspace
REPO=$WORKSPACE/lecseg
DATA=$REPO/data

# ── 1. System deps ────────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq ffmpeg libsndfile1 git rsync

# ── 2. Clone / copy project ───────────────────────────────────────────────────
# Option A: if you push to GitHub first
# git clone https://github.com/YOUR_USER/lecseg.git $REPO

# Option B: rsync from local (run this from YOUR machine, not the instance)
# rsync -avz --exclude '.venv' --exclude '__pycache__' --exclude 'data/raw' \
#   -e "ssh -p PORT" ./ root@HOST:$REPO/
# Then continue from step 3 on the instance.

cd $REPO

# ── 3. Python env ─────────────────────────────────────────────────────────────
python -m pip install --upgrade pip -q
pip install -q \
    torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -q \
    sentence-transformers \
    transformers \
    open-clip-torch \
    paddlepaddle-gpu paddleocr \
    librosa soundfile \
    spacy segeval scikit-learn numpy \
    yt-dlp rich typer
python -m spacy download en_core_web_sm -q

# Install TransNetV2
pip install -q "transnetv2 @ git+https://github.com/soCzech/TransNetV2.git" || \
    pip install -q transnetv2-pytorch

# Install lecseg itself (editable)
pip install -e . -q

# ── 4. Upload raw videos from local machine ───────────────────────────────────
# Run this block FROM YOUR LOCAL MACHINE (PowerShell), then SSH back in:
#
#   $HOST = "IP_ADDRESS"
#   $PORT = "PORT_NUMBER"
#   scp -P $PORT -r data/raw/ root@${HOST}:/workspace/lecseg/data/raw/
#   scp -P $PORT -r data/transcripts/ root@${HOST}:/workspace/lecseg/data/transcripts/
#   scp -P $PORT -r data/sentences/ root@${HOST}:/workspace/lecseg/data/sentences/
#
# Estimated upload time at 6113 Mbps: ~2-3 min for ~35 GB
# Wait for upload to finish, then continue:

echo ">>> Waiting — upload data/raw/ before proceeding <<<"
echo ">>> Press Enter when upload is complete..."
read -r

# ── 5. Run all preprocessing tasks in parallel ────────────────────────────────
echo "=== Starting all preprocessing tasks ==="
mkdir -p $DATA/{sentences,shots,ocr,prosody,emb_text,emb_visual,features}

# T15 — Sentence splitting (fast, must finish before T19)
echo "[T15] Sentence splitting..."
python src/lecseg/preprocess/sentence_split.py
echo "[T15] DONE"

# T16, T17, T18, T19, T20 — run in parallel
echo "[T16-T20] Launching parallel tasks..."

python src/lecseg/preprocess/shot_detection.py \
    > $WORKSPACE/t16.log 2>&1 &
PID_T16=$!

python src/lecseg/preprocess/ocr.py \
    > $WORKSPACE/t17.log 2>&1 &
PID_T17=$!

python src/lecseg/preprocess/prosody.py --workers 8 \
    > $WORKSPACE/t18.log 2>&1 &
PID_T18=$!

python src/lecseg/features/text_embeddings.py --model mpnet \
    > $WORKSPACE/t19.log 2>&1 &
PID_T19=$!

# Wait for T19 (needed before T20 alignment, and T20 needs shots from T16)
wait $PID_T19
echo "[T19] Text embeddings DONE"

wait $PID_T16
echo "[T16] Shot detection DONE"

# T20 — Visual embeddings (needs T16 shots done)
python src/lecseg/features/visual_embeddings.py \
    > $WORKSPACE/t20.log 2>&1 &
PID_T20=$!

wait $PID_T17 && echo "[T17] OCR DONE"
wait $PID_T18 && echo "[T18] Prosody DONE"
wait $PID_T20 && echo "[T20] Visual embeddings DONE"

# T21 — Align all modalities
echo "[T21] Aligning modalities..."
python src/lecseg/features/alignment.py
echo "[T21] DONE"

echo ""
echo "=== ALL PREPROCESSING COMPLETE ==="

# ── 6. Verify outputs ─────────────────────────────────────────────────────────
echo "Output counts:"
echo "  sentences : $(ls $DATA/sentences/ 2>/dev/null | wc -l)/30"
echo "  shots     : $(ls $DATA/shots/ 2>/dev/null | wc -l)/30"
echo "  ocr       : $(ls $DATA/ocr/ 2>/dev/null | wc -l)/30"
echo "  prosody   : $(ls $DATA/prosody/ 2>/dev/null | wc -l)/30"
echo "  emb_text  : $(ls $DATA/emb_text/mpnet/ 2>/dev/null | wc -l)/30"
echo "  emb_visual: $(ls $DATA/emb_visual/ 2>/dev/null | wc -l)/30"
echo "  features  : $(ls $DATA/features/ 2>/dev/null | wc -l)/30"

# ── 7. Download results back to local machine ─────────────────────────────────
# Run FROM YOUR LOCAL MACHINE (PowerShell):
#
#   $HOST = "IP_ADDRESS"
#   $PORT = "PORT_NUMBER"
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/sentences/ data/
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/shots/ data/
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/ocr/ data/
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/prosody/ data/
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/emb_text/ data/
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/emb_visual/ data/
#   scp -P $PORT -r root@${HOST}:/workspace/lecseg/data/features/ data/
#
# THEN DESTROY THE INSTANCE IMMEDIATELY to stop billing.

echo ""
echo ">>> DONE. Download outputs and DESTROY the instance. <<<"
