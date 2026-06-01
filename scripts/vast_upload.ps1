# Usage: .\scripts\vast_upload.ps1 -IP "1.2.3.4" -Port 12345
param(
    [Parameter(Mandatory)][string]$IP,
    [Parameter(Mandatory)][int]$Port
)

$SSH = "root@$IP"
$SCP = "scp -o StrictHostKeyChecking=no -i $env:USERPROFILE\.ssh\id_rsa -P $Port"
$BASE = "G:\THESIS\PreThesis2_TopicSegmentation"

Write-Host "=== Uploading data to vast.ai ===" -ForegroundColor Cyan

# Setup workspace
Write-Host "[1/5] Creating workspace..." -ForegroundColor Yellow
ssh -o StrictHostKeyChecking=no -i "$env:USERPROFILE\.ssh\id_rsa" -p $Port $SSH `
    "mkdir -p /workspace/lecseg/sentences /workspace/lecseg/embeddings/bge /workspace/lecseg/gt_hier /workspace/lecseg/models /workspace/lecseg/results"

# Upload sentences
Write-Host "[2/5] Uploading sentences (~50MB)..." -ForegroundColor Yellow
& $SCP.Split() -r "$BASE\data\sentences\" "${SSH}:/workspace/lecseg/sentences/"

# Upload BGE embeddings (needed for contrastive training reference)
Write-Host "[3/5] Uploading BGE embeddings (~90MB)..." -ForegroundColor Yellow
& $SCP.Split() -r "$BASE\data\embeddings\bge\" "${SSH}:/workspace/lecseg/embeddings/bge/"

# Upload GT annotations
Write-Host "[4/5] Uploading GT annotations (~1MB)..." -ForegroundColor Yellow
& $SCP.Split() -r "$BASE\data\gt_hier\" "${SSH}:/workspace/lecseg/gt_hier/"

# Upload scripts
Write-Host "[5/5] Uploading scripts..." -ForegroundColor Yellow
& $SCP.Split() `
    "$BASE\scripts\vast_stella.py" `
    "$BASE\scripts\vast_contrastive.py" `
    "$BASE\scripts\vast_crossencoder.py" `
    "${SSH}:/workspace/lecseg/"

Write-Host "`n=== Upload done! Now SSH in and run: ===" -ForegroundColor Green
Write-Host "ssh -p $Port $SSH" -ForegroundColor White
Write-Host "pip install -q sentence-transformers==3.3.1 torch scikit-learn numpy" -ForegroundColor White
Write-Host "cd /workspace/lecseg" -ForegroundColor White
Write-Host "screen -S stella -dm bash -c 'python vast_stella.py 2>&1 | tee stella.log'" -ForegroundColor White
Write-Host "screen -S contrastive -dm bash -c 'python vast_contrastive.py 2>&1 | tee contrastive.log'" -ForegroundColor White
Write-Host "screen -S crossencoder -dm bash -c 'python vast_crossencoder.py 2>&1 | tee crossencoder.log'" -ForegroundColor White
Write-Host "watch -n 15 'echo STELLA: && tail -2 stella.log; echo CONTRASTIVE: && tail -2 contrastive.log; echo CROSSENCODER: && tail -2 crossencoder.log'" -ForegroundColor White
