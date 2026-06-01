#!/bin/bash
# LECSEG vast.ai setup — run this on the remote instance after connecting.
# Launches 3 parallel jobs via screen sessions.
# Usage: bash vast_setup.sh

set -e
echo "=== LECSEG vast.ai setup ==="
echo "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)"

# ── 1. Install deps ──────────────────────────────────────────────────────────
pip install -q sentence-transformers==3.3.1 scikit-learn numpy torch --extra-index-url https://download.pytorch.org/whl/cu121

# ── 2. Create workspace ──────────────────────────────────────────────────────
mkdir -p /workspace/lecseg/{sentences,embeddings/{bge,stella},gt_hier,models,results}

echo "Workspace ready."
echo ""
echo "=== NEXT STEPS ==="
echo "1. Upload data from local:"
echo "   scp -P PORT -r data/sentences root@IP:/workspace/lecseg/sentences/"
echo "   scp -P PORT -r data/embeddings/bge root@IP:/workspace/lecseg/embeddings/bge/"
echo "   scp -P PORT -r data/gt_hier root@IP:/workspace/lecseg/gt_hier/"
echo ""
echo "2. Upload scripts:"
echo "   scp -P PORT scripts/vast_stella.py scripts/vast_contrastive.py scripts/vast_crossencoder.py root@IP:/workspace/lecseg/"
echo ""
echo "3. Launch all 3 jobs:"
echo "   screen -S stella -dm bash -c 'cd /workspace/lecseg && python vast_stella.py 2>&1 | tee stella.log'"
echo "   screen -S contrastive -dm bash -c 'cd /workspace/lecseg && python vast_contrastive.py 2>&1 | tee contrastive.log'"
echo "   screen -S crossencoder -dm bash -c 'cd /workspace/lecseg && python vast_crossencoder.py 2>&1 | tee crossencoder.log'"
echo ""
echo "4. Monitor:"
echo "   watch -n 10 'echo STELLA: && tail -3 stella.log; echo CONTRASTIVE: && tail -3 contrastive.log; echo CROSSENCODER: && tail -3 crossencoder.log'"
