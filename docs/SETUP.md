# ⚙️ SETUP — Detailed Environment Setup

**For the standard new-team-member walkthrough → see `START_HERE.md` in the project root.**
**This file is the deeper reference for things that broke in `START_HERE.md`.**

---

## Order of operations

1. Install system tools (T01).
2. Clone the project (T01).
3. Create + activate the virtual environment (T01 step 3).
4. Install Python deps (T03).
5. Install Ollama + pull models (T04).
6. Run smoke test (T05).

If something breaks, search `docs/TROUBLESHOOTING.md`.

---

## Virtual environment — full reference

Create:
```
python -m venv .venv
```

Activate:
```
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# If you get an execution-policy error:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1

# Windows cmd.exe
.\.venv\Scripts\activate.bat

# Mac/Linux/Git Bash
source .venv/bin/activate
```

Verify:
```
which python    # should point inside .venv
python --version    # 3.11.x
```

Deactivate (when done for the day):
```
deactivate
```

---

## GPU setup (optional, but Phase 4 onwards is 5-10× faster with one)

### NVIDIA on Windows / Linux

1. Install latest NVIDIA driver: https://www.nvidia.com/drivers/
2. Install CUDA 12.1 runtime: https://developer.nvidia.com/cuda-12-1-0-download-archive
3. Reinstall PyTorch with CUDA wheels:
   ```
   pip uninstall -y torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
4. Verify:
   ```
   python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```
   Expected: `True NVIDIA GeForce RTX ...`.

### Apple Silicon (M1/M2/M3)

```
pip install torch torchvision torchaudio
python -c "import torch; print(torch.backends.mps.is_available())"   # → True
```
Most of our code falls back gracefully to MPS or CPU on Mac.

---

## CUDA + cuDNN versions cheat-sheet

| Component | Minimum | Recommended |
|---|---|---|
| NVIDIA Driver | 525 | latest |
| CUDA toolkit | 11.8 | 12.1 |
| cuDNN | 8.6 | 9.0 |
| PyTorch | 2.2 | 2.4 |

Do NOT mix CUDA 11 + PyTorch built for CUDA 12. Match your wheel to your toolkit.

---

## Disk space budget

| Item | Disk |
|---|---|
| `.venv/` (PyTorch, transformers, …) | ~5 GB |
| Whisper model cache | ~3 GB |
| Ollama models (Llama 3.1 8B + Mistral 7B) | ~10 GB |
| `data/raw/` (30 videos + audio) | **~90 GB** |
| Embeddings + features | ~10 GB |
| Results / checkpoints | ~5 GB |
| **Total budget** | **~130 GB** |

→ Mount `data/raw/` on an external SSD (200 GB free recommended). See T10 for the symlink command.

---

## Editor setup (VS Code)

1. Install VS Code + extensions (Python, LaTeX Workshop, GitLens, Markdown All in One). See T01.
2. Open the project folder.
3. `Ctrl+Shift+P` → "Python: Select Interpreter" → choose `.venv/bin/python`.
4. `Ctrl+Shift+P` → "Format Document With…" → Black.
5. Enable auto-save: File → Auto Save.

---

## Pre-commit hooks (optional but nice)

```
pip install pre-commit
pre-commit install
```

Now every `git commit` runs `ruff` and `black` on the staged files.

---

## Recreating the environment from scratch

If your venv gets weird:

```
deactivate
rm -rf .venv          # Mac/Linux
rmdir /S /Q .venv     # Windows
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```
