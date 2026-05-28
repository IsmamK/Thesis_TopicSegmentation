#!/usr/bin/env bash
# =============================================================================
#  LECSEG — vast.ai full preprocessing run
#  Instance: RTX 5060 Ti 16GB | PyTorch (Vast) template | CUDA 12.9
#
#  PASTE THIS ENTIRE SCRIPT into the instance SSH terminal:
#    bash vastai_run.sh 2>&1 | tee /workspace/master.log
#
#  RECOVERY: If interrupted, re-run the same command.
#            Already-completed tasks are skipped automatically.
# =============================================================================
set -uo pipefail

# ── Colours & helpers ─────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo -e "${GREEN}[$(date +%H:%M:%S)] ✔ $*${NC}"; }
warn() { echo -e "${YELLOW}[$(date +%H:%M:%S)] ⚠ $*${NC}"; }
fail() { echo -e "${RED}[$(date +%H:%M:%S)] ✘ $*${NC}"; }

# ── Paths ─────────────────────────────────────────────────────────────────────
WORKSPACE=/workspace
REPO=$WORKSPACE/lecseg
DATA=$REPO/data
STATE=$WORKSPACE/session_state.json
LOG=$WORKSPACE

# ── State helpers (recovery) ──────────────────────────────────────────────────
init_state() {
    if [ ! -f "$STATE" ]; then
        cat > "$STATE" <<'EOF'
{
  "setup_done": false,
  "T15_done": false,
  "T16_done": false,
  "T17_done": false,
  "T18_done": false,
  "T19_done": false,
  "T20_done": false,
  "T21_done": false
}
EOF
        log "Created fresh session_state.json"
    else
        warn "Found existing session_state.json — skipping completed tasks"
    fi
}

is_done()  { python3 -c "import json,sys; d=json.load(open('$STATE')); sys.exit(0 if d.get('$1') else 1)" 2>/dev/null; }
mark_done() {
    python3 - "$1" <<'PYEOF'
import json, sys
k = sys.argv[1]
with open('/workspace/session_state.json','r') as f: d = json.load(f)
d[k] = True
with open('/workspace/session_state.json','w') as f: json.dump(d, f, indent=2)
PYEOF
    ok "$1 marked done in session_state.json"
}

progress_bar() {
    local done=$1 total=$2 label=$3
    local pct=$(( done * 100 / total ))
    local filled=$(( done * 30 / total ))
    local bar=""
    for ((i=0;i<filled;i++)); do bar+="█"; done
    for ((i=filled;i<30;i++)); do bar+="░"; done
    printf "${BOLD}[%s] %s %d/%d (%d%%)${NC}\n" "$bar" "$label" "$done" "$total" "$pct"
}

print_status() {
    echo ""
    echo -e "${BOLD}══════════════════════════════════════════${NC}"
    echo -e "${BOLD}  LECSEG preprocessing — task status${NC}"
    echo -e "${BOLD}══════════════════════════════════════════${NC}"
    for task in setup T15 T16 T17 T18 T19 T20 T21; do
        if is_done "${task}_done" 2>/dev/null; then
            echo -e "  ${GREEN}✔${NC} $task"
        else
            echo -e "  ${YELLOW}○${NC} $task"
        fi
    done
    echo -e "${BOLD}══════════════════════════════════════════${NC}"
    echo ""
}

# ── 0. Init ───────────────────────────────────────────────────────────────────
mkdir -p $WORKSPACE
init_state
print_status

# ── 1. System + Python deps ───────────────────────────────────────────────────
if ! is_done "setup_done"; then
    log "Installing system dependencies..."
    apt-get update -qq && apt-get install -y -qq ffmpeg libsndfile1 rsync 2>/dev/null
    ok "System deps installed"

    log "Installing Python packages (this takes ~4 min)..."
    pip install -q --upgrade pip

    # Core ML stack
    pip install -q \
        sentence-transformers \
        open-clip-torch \
        paddlepaddle-gpu paddleocr \
        librosa soundfile \
        spacy segeval scikit-learn numpy \
        yt-dlp rich typer \
        opencv-python-headless 2>&1 | tail -3

    # TransNetV2
    pip install -q "transnetv2 @ git+https://github.com/soCzech/TransNetV2.git" 2>/dev/null || \
        pip install -q transnetv2-pytorch 2>/dev/null || \
        warn "TransNetV2 install failed — shot detection will use fallback"

    python3 -m spacy download en_core_web_sm -q 2>/dev/null
    ok "Python packages installed"

    # Install lecseg package
    cd $REPO
    pip install -e . -q 2>/dev/null || warn "lecseg editable install failed — scripts will still work"
    ok "lecseg installed"

    mark_done "setup_done"
else
    ok "Setup already done — skipping"
fi

print_status

# ── 2. Wait for data upload ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  UPLOAD DATA FROM YOUR LOCAL MACHINE NOW${NC}"
echo -e "${BOLD}  Run these commands in a NEW PowerShell window on your PC:${NC}"
echo ""
echo -e "${CYAN}  \$HOST = '85.10.218.46'${NC}"
echo -e "${CYAN}  \$PORT = '46035'${NC}"
echo -e "${CYAN}  scp -P \$PORT -r data/raw/ root@\${HOST}:/workspace/lecseg/data/raw/${NC}"
echo -e "${CYAN}  scp -P \$PORT -r data/transcripts/ root@\${HOST}:/workspace/lecseg/data/transcripts/${NC}"
echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Wait until at least 1 raw video exists
log "Waiting for raw video upload..."
while true; do
    COUNT=$(ls $DATA/raw/ 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        ok "Detected $COUNT raw video folders — proceeding"
        break
    fi
    printf "\r  Waiting for data/raw/ ... (checking every 10s)"
    sleep 10
done

# Wait for all 30 (or at least 28 to handle 3 replacements in flight)
log "Waiting for all videos to finish uploading..."
while true; do
    COUNT=$(ls $DATA/raw/ 2>/dev/null | wc -l)
    printf "\r  ${GREEN}%d/30${NC} video folders uploaded..." "$COUNT"
    [ "$COUNT" -ge 30 ] && break
    sleep 15
done
echo ""
ok "All 30 videos uploaded"

mkdir -p $DATA/{sentences,shots,ocr,prosody,emb_text/mpnet,emb_visual,features}

# ── 3. T15 — Sentence splitting (must run first) ──────────────────────────────
if ! is_done "T15_done"; then
    log "T15 — Sentence splitting (sequential, ~2 min)..."
    cd $REPO
    python3 src/lecseg/preprocess/sentence_split.py > $LOG/t15.log 2>&1
    COUNT=$(ls $DATA/sentences/ 2>/dev/null | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        ok "T15 DONE — $COUNT sentence files"
        mark_done "T15_done"
    else
        fail "T15 produced no output — check $LOG/t15.log"
        exit 1
    fi
else
    ok "T15 already done — skipping"
fi

print_status

# ── 4. T16 + T17 + T18 + T19 — parallel ──────────────────────────────────────
log "Launching T16/T17/T18/T19 in parallel..."
cd $REPO

# T16 — Shot detection
if ! is_done "T16_done"; then
    python3 src/lecseg/preprocess/shot_detection.py > $LOG/t16.log 2>&1 &
    PID_T16=$!
    log "T16 shot detection started (PID $PID_T16)"
else
    ok "T16 already done — skipping"; PID_T16=""
fi

# T17 — OCR
if ! is_done "T17_done"; then
    python3 src/lecseg/preprocess/ocr.py > $LOG/t17.log 2>&1 &
    PID_T17=$!
    log "T17 OCR started (PID $PID_T17)"
else
    ok "T17 already done — skipping"; PID_T17=""
fi

# T18 — Prosody
if ! is_done "T18_done"; then
    python3 src/lecseg/preprocess/prosody.py --workers 8 > $LOG/t18.log 2>&1 &
    PID_T18=$!
    log "T18 prosody started (PID $PID_T18)"
else
    ok "T18 already done — skipping"; PID_T18=""
fi

# T19 — Text embeddings
if ! is_done "T19_done"; then
    python3 src/lecseg/features/text_embeddings.py --model mpnet > $LOG/t19.log 2>&1 &
    PID_T19=$!
    log "T19 text embeddings started (PID $PID_T19)"
else
    ok "T19 already done — skipping"; PID_T19=""
fi

# ── 5. Live progress monitor while parallel tasks run ─────────────────────────
log "Monitoring parallel tasks (updates every 30s)..."
while true; do
    ALL_DONE=true

    for task_info in "T16:shots:$PID_T16" "T17:ocr:$PID_T17" "T18:prosody:$PID_T18" "T19:emb_text/mpnet:$PID_T19"; do
        IFS=: read -r TASK DIR PID <<< "$task_info"
        if is_done "${TASK}_done" 2>/dev/null; then continue; fi
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            COUNT=$(ls $DATA/$DIR/ 2>/dev/null | wc -l)
            progress_bar "$COUNT" 30 "$TASK"
            ALL_DONE=false
        else
            # Process finished — check output
            COUNT=$(ls $DATA/$DIR/ 2>/dev/null | wc -l)
            if [ "$COUNT" -gt 0 ]; then
                ok "$TASK finished — $COUNT files"
                mark_done "${TASK}_done"
            else
                fail "$TASK process ended with no output — check $LOG/${TASK,,}.log"
            fi
        fi
    done

    $ALL_DONE && break
    sleep 30
done

print_status

# ── 6. T20 — Visual embeddings (after T16 shots done) ────────────────────────
if ! is_done "T20_done"; then
    if ! is_done "T16_done"; then
        fail "T16 not done — cannot run T20"; exit 1
    fi
    log "T20 — CLIP visual embeddings (~12 min)..."
    python3 src/lecseg/features/visual_embeddings.py > $LOG/t20.log 2>&1 &
    PID_T20=$!
    while kill -0 $PID_T20 2>/dev/null; do
        COUNT=$(ls $DATA/emb_visual/ 2>/dev/null | wc -l)
        progress_bar "$COUNT" 30 "T20 CLIP visual"
        sleep 20
    done
    COUNT=$(ls $DATA/emb_visual/ 2>/dev/null | wc -l)
    ok "T20 DONE — $COUNT visual embedding files"
    mark_done "T20_done"
else
    ok "T20 already done — skipping"
fi

# ── 7. T21 — Alignment (all modalities done) ─────────────────────────────────
if ! is_done "T21_done"; then
    log "T21 — Aligning all modalities (~1 min)..."
    python3 src/lecseg/features/alignment.py > $LOG/t21.log 2>&1
    COUNT=$(ls $DATA/features/ 2>/dev/null | wc -l)
    ok "T21 DONE — $COUNT aligned feature files"
    mark_done "T21_done"
else
    ok "T21 already done — skipping"
fi

# ── 8. Final summary ──────────────────────────────────────────────────────────
print_status

echo ""
echo -e "${BOLD}${GREEN}════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ALL PREPROCESSING COMPLETE  ${NC}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo "Output summary:"
printf "  %-20s %s\n" "sentences/"    "$(ls $DATA/sentences/    2>/dev/null | wc -l)/30"
printf "  %-20s %s\n" "shots/"        "$(ls $DATA/shots/        2>/dev/null | wc -l)/30"
printf "  %-20s %s\n" "ocr/"          "$(ls $DATA/ocr/          2>/dev/null | wc -l)/30"
printf "  %-20s %s\n" "prosody/"      "$(ls $DATA/prosody/      2>/dev/null | wc -l)/30"
printf "  %-20s %s\n" "emb_text/mpnet" "$(ls $DATA/emb_text/mpnet/ 2>/dev/null | wc -l)/30"
printf "  %-20s %s\n" "emb_visual/"   "$(ls $DATA/emb_visual/   2>/dev/null | wc -l)/30"
printf "  %-20s %s\n" "features/"     "$(ls $DATA/features/     2>/dev/null | wc -l)/30"
echo ""
echo -e "${BOLD}NEXT STEPS — run on YOUR LOCAL MACHINE:${NC}"
echo ""
echo "  # Download all outputs (PowerShell):"
echo "  \$HOST='85.10.218.46'; \$PORT='46035'"
echo "  @('sentences','shots','ocr','prosody','emb_text','emb_visual','features') | ForEach-Object {"
echo "      scp -P \$PORT -r root@\${HOST}:/workspace/lecseg/data/\$_/ data/"
echo "  }"
echo ""
echo "  # DESTROY THE INSTANCE on vast.ai dashboard immediately after download!"
echo ""
echo "  # Then run locally:"
echo "  .venv\Scripts\python.exe scripts/run_eval.py --verbose   # T29 ablation"
echo ""
echo -e "${BOLD}${YELLOW}Total billed time: ~$(( ($(date +%s) - START_TIME) / 60 )) minutes${NC}"
