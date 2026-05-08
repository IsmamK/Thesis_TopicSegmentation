# 🆘 TROUBLESHOOTING — When Things Break

**Search this file first when you get an error.** The 5 most common problems are at the top with copy-paste fixes.

---

## 🚑 Top 5 panic-button fixes

### 1. `(.venv)` is not in my prompt

You forgot to activate the virtual environment. Run:

```
# Windows PowerShell / cmd
.\.venv\Scripts\activate

# Mac / Linux / Git Bash
source .venv/bin/activate
```

### 2. `python: command not found` or wrong version

You skipped the "Add Python to PATH" tick during install. Reinstall Python 3.11 64-bit from https://python.org and tick the PATH box. Then **close and reopen every terminal**.

### 3. `ffmpeg: command not found`

Add `C:\ffmpeg\bin` to PATH (Windows). On Mac: `brew install ffmpeg`. **Then close and reopen every terminal.**

### 4. `ModuleNotFoundError: No module named 'X'`

You are not in the venv, OR you didn't install dependencies. Run:

```
pip install -e .            # if you are in the project root
pip install pyyaml rich     # bare minimum
```

### 5. `ollama: connection refused`

Ollama service isn't running. On Windows: open Services (`services.msc`) → start Ollama. On Mac: open the Ollama app from Applications.

---

## Detailed problems by task

### T01 — Prerequisites

| Problem | Fix |
|---|---|
| `python --version` shows 3.12 | Install 3.11 specifically. They coexist. Ensure 3.11 is first in PATH. |
| MiKTeX install hangs | Disable antivirus during install, re-enable after. |
| FFmpeg zip extracts oddly | Final path must be `C:\ffmpeg\bin\ffmpeg.exe`. Move files up if it's nested. |

### T03 — Python deps

| Problem | Fix |
|---|---|
| `pip install` hangs on torch | Normal — PyTorch is ~2 GB. Be patient. |
| `ERROR: torch not found for your platform` | Wrong Python (not 3.11) or 32-bit Python. Reinstall 3.11 64-bit. |
| `paddleocr` install fails | Skip until T17. Comment out the line in `pyproject.toml`. |
| Mac M1/M2 PyTorch on CPU | `pip install torch --index-url https://download.pytorch.org/whl/nightly/cpu` |

### T04 — Ollama

| Problem | Fix |
|---|---|
| `ollama pull` stuck at 0% | Cloudflare can block. Retry, or try a phone hotspot. |
| `Error: model requires more memory` | Use a smaller model: `ollama pull llama3.2:3b`. Update configs. |
| Ollama not in tray | `services.msc` → start Ollama (Windows). Reopen the app (Mac). |
| GPU not used | `ollama ps` while a model runs. If GPU not listed → install CUDA drivers. |

### T10 — Download videos

| Problem | Fix |
|---|---|
| `Video unavailable` | YouTube region-locked. Pick a similar video. |
| Slow download | Campus Wi-Fi caps. Try overnight or hotspot. |
| Disk fills up | 30 videos × ~3 GB = ~90 GB. Need 200 GB free. Symlink to external SSD. |
| `yt-dlp` breaks | `pip install -U yt-dlp` — YouTube changes. |

### T14 — Whisper

| Problem | Fix |
|---|---|
| `No CUDA devices` | You don't have a GPU. Falls back to CPU automatically. Slower but works. |
| Out of GPU memory | `beam_size=1` and use `medium` model. |
| Gibberish transcript | `vad_filter=False` or normalise audio: `ffmpeg -i a.wav -filter:a loudnorm a_norm.wav`. |

### Git problems

| Problem | Fix |
|---|---|
| `git push` rejected | Pull first: `git pull --rebase`. |
| Large file blocked | Use Git LFS: `git lfs track "*.npy"` then re-commit. |
| Merge conflicts | Open the file, look for `<<<<` markers, decide which version to keep. Save. `git add` the file. `git commit`. |

### LaTeX problems

| Problem | Fix |
|---|---|
| Citation `[?]` in PDF | Run `bibtex main` between two `pdflatex` runs. |
| `\usepackage{X}` errors | MiKTeX prompts to install on demand → click Install. Or `mpm --install=X`. |
| Overfull hbox warnings | Find the line in the log; rewrite the sentence. Cosmetic, not fatal. |

### Streamlit problems

| Problem | Fix |
|---|---|
| `streamlit run` hangs | Try a different port: `streamlit run app.py --server.port=8502`. |
| Runs but blank page | Hard refresh (Ctrl+Shift+R). Check console (F12) for errors. |

---

## 🧯 When nothing works

1. Run `python scripts/today.py` — it confirms basics work.
2. Run `python scripts/context.py > context.txt` and paste it to Claude with your error message.
3. Ask the team channel with: (a) the task ID, (b) the exact command, (c) the full error.

## 🔄 Reset switches

If you are very stuck:

```
# Reinstall everything Python
rm -rf .venv
python -m venv .venv
.\.venv\Scripts\activate           # Windows  (or: source .venv/bin/activate)
pip install -e .
pip install pyyaml rich typer

# Throw away local edits and re-pull
git stash
git pull
```

⚠️ `git stash` saves your edits in a side-pocket, not deleted. To recover: `git stash pop`.
