# T03 — Install Python Dependencies & Bootstrap src/

**Phase 1 · Setup · Estimated time: 30 minutes (mostly download waiting) · Owner: Ismam**

---

## 🎯 What you are doing
Installing all Python libraries we need (PyTorch, Whisper, etc.) and creating the skeleton of our code package `src/lecseg/`.

## 🤔 Why
These libraries do the heavy lifting: speech recognition, embeddings, neural networks, evaluation metrics. The skeleton gives us a structured place to put our code instead of ad-hoc scripts.

## ✅ How to know you are done
- `python -c "import torch, transformers, sentence_transformers, faster_whisper, segeval; print('ok')"` prints `ok`.
- `python -m lecseg.cli --help` prints our CLI help.
- `pytest` runs (even with zero tests).

---

## 📝 Steps

### Step 1 — Make sure your venv is active
Your prompt should start with `(.venv)`. If not: see [docs/SETUP.md](../docs/SETUP.md).

### Step 2 — Ask Claude

Paste this prompt to Claude:

> Execute task T03 from `tasks/T03_install_python_deps.md`. Read `internal/CLAUDE.md` first. When writing `pyproject.toml`, use exactly the dependency list in this file. After installing, run the verification commands and report pass/fail.

Claude will:
1. Write `pyproject.toml` with the dependency list below.
2. Run `pip install -e .` (editable install, so code changes take effect immediately).
3. Create the `src/lecseg/` package structure with a minimal CLI skeleton:
   - `src/lecseg/__init__.py` — version string
   - `src/lecseg/cli.py` — typer app with subcommands (empty bodies for now): `download, transcribe, ocr, shots, prosody, embed, segment, evaluate, report, run`
   - Placeholder `src/lecseg/<module>/__init__.py` files
4. Write `tests/test_smoke.py` with one test that imports the package.
5. Run `pytest`. If it passes, commit.

### Dependency list (Claude will put this into pyproject.toml)

```toml
[project]
name = "lecseg"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
  # Core ML
  "torch>=2.2,<2.6",
  "torchvision",
  "torchaudio",
  "transformers>=4.40",
  "sentence-transformers>=3.0",
  "scikit-learn>=1.4",
  # ASR
  "faster-whisper>=1.0",
  "openai-whisper>=20231117",
  "pysbd>=0.3.4",
  # OCR & vision
  "paddleocr>=2.7",
  "opencv-python-headless>=4.9",
  "pillow>=10.2",
  # Audio / prosody
  "librosa>=0.10",
  "soundfile>=0.12",
  # Segmentation metrics
  "segeval>=2.0.11",
  "nltk>=3.8",          # for TextTiling
  # Dataset / download
  "yt-dlp>=2024.4.9",
  "datasets>=2.19",
  "huggingface-hub>=0.22",
  # Orchestration
  "hydra-core>=1.3",
  "typer>=0.12",
  "rich>=13.7",
  "tqdm>=4.66",
  # LLM (local via Ollama)
  "ollama>=0.2",
  # Data tooling
  "pandas>=2.2",
  "numpy>=1.26,<2.0",
  "scipy>=1.11",
  "matplotlib>=3.8",
  "pyarrow>=15.0",
  # Web demo
  "streamlit>=1.33",
  # Quality
  "pytest>=8.0",
  "ruff>=0.4",
  "black>=24.3",
  # Utilities
  "python-dotenv>=1.0",
  "pyyaml>=6.0",
  "jsonlines>=4.0",
]

[project.optional-dependencies]
dev = ["jupyter", "ipykernel", "ipywidgets"]

[project.scripts]
lecseg = "lecseg.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Step 3 — Verify

```
python -c "import torch; print('torch', torch.__version__)"
python -c "import faster_whisper; print('whisper ok')"
python -c "import segeval; print('segeval ok')"
lecseg --help
pytest
```

All 5 commands must succeed. If they do, you are done.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **PyTorch** | Deep-learning framework. Think "NumPy but on GPUs with auto-differentiation." |
| **transformers (Hugging Face)** | A library that wraps thousands of pretrained AI models so you can use one with 3 lines of code. |
| **faster-whisper** | A reimplementation of OpenAI's Whisper speech-recognition model that is 4× faster. |
| **Hydra** | Config-file library. Lets us swap hyperparameters via YAML files without editing code. |
| **Typer** | Library that makes CLI commands from Python functions. Used for our `lecseg` command. |
| **Editable install (`pip install -e .`)** | Installs our code in a way that picks up edits live. |

More at [docs/CONCEPTS.md](../docs/CONCEPTS.md).

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` hangs on torch | Normal — PyTorch is ~2 GB. Be patient. |
| `ERROR: torch not found for your platform` | You have the wrong Python version (not 3.11) or 32-bit Python on Windows. Reinstall Python 3.11 64-bit. |
| `paddleocr` install fails | Skip it for now (we'll install it in T17). Comment out the line in pyproject.toml. |
| Mac M1/M2: torch CPU-only | For GPU on Apple Silicon: `pip install torch --index-url https://download.pytorch.org/whl/nightly/cpu` |

---

## ➡️ When done

```
python scripts/mark_done.py T03
python scripts/next.py
```
