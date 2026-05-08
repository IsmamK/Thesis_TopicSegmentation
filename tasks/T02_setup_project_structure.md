# T02 — Create Project Folder Structure

**Phase 1 · Setup · Estimated time: 15 minutes · Owner: Ismam (once)**

---

## 🎯 What you are doing
Creating empty source-code folders (`src/`, `configs/`, etc.), installing the BracU LaTeX thesis template, and initializing Git LFS for large binary files.

## 🤔 Why
Every later task assumes these folders exist in a fixed layout. Fixing the layout once at the start prevents messy reorganizations later.

## ✅ How to know you are done
- Running `ls` (Mac/Linux) or `dir` (Windows) in the project root shows: `src/ configs/ data/ results/ thesis/ paper/ webapp/ scripts/ tasks/ docs/ internal/ papers_summary/`
- `thesis/main.tex` exists and can compile (`cd thesis && pdflatex main.tex`)

---

## 📝 Steps

### Step 1 — Open the project in a terminal

Make sure you see `(.venv)` at the start of your prompt. If you don't:

```
# Windows
.\.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

### Step 2 — Ask Claude to do it

Open a Claude Code session in this folder. Paste **exactly** this prompt:

> Read internal/CLAUDE.md. Then perform Task T02 following `tasks/T02_setup_project_structure.md`. Execute every step, stop only if you hit an error, and report what you created.

Claude will then do the following automatically:

1. Create these folders (empty, with a README.md stub in each):
   - `src/lecseg/` (with submodules `data/`, `preprocess/`, `features/`, `models/`, `refine/`, `eval/`, `viz/`, `report/`)
   - `src/lecseg/__init__.py`
   - `configs/` (with a `defaults.yaml`)
   - `data/` (with subfolders `raw/`, `whisper/`, `sentences/`, `shots/`, `ocr/`, `prosody/`, `emb_text/`, `emb_visual/`, `features/`, `gt/`, `gt_hier/`, `release/`, `llm_cache/`)
   - `results/`
   - `thesis/` (copy from `C:/Users/User/Downloads/FINAL YEAR THESIS Template_CSE400_Fall 2024 ONWARDS/`)
   - `paper/`
   - `webapp/`
   - `tests/`
   - `notebooks/`
2. Copy the BracU LaTeX template into `thesis/` and edit `thesis/core/titlepage.tex` with our team info.
3. Create `.gitignore` excluding: `.venv/`, `*.mp4`, `*.wav`, `*.mkv`, `data/raw/`, `data/webapp_cache/`, `__pycache__/`, `.DS_Store`, `*.pyc`, `.ipynb_checkpoints/`, `results/*/checkpoints/`.
4. Initialize Git LFS and track: `*.npy`, `*.npz`, large `*.csv`, `*.pdf` (in thesis/images), `*.pkl`, `*.pt`.
5. Add a `Makefile` with these targets: `install test lint reproduce thesis paper webapp clean`.
6. Add `pyproject.toml` with project metadata (fill in actual deps in T03).
7. Run `git add . && git commit -m "chore: bootstrap project structure (T02)"`.

### Step 3 — Verify

After Claude finishes, run:

```
python scripts/mark_progress.py T02 doing
ls src/lecseg/
ls thesis/
cd thesis && pdflatex -interaction=nonstopmode main.tex
cd ..
```

The last command should produce `thesis/main.pdf`. If so, the template is working.

---

## 🧠 Concepts you will encounter

| Term | Plain-English meaning | Read more |
|---|---|---|
| **Git LFS** | "Large File Storage" — a Git add-on that stores big files (embeddings, PDFs) efficiently. Required because plain Git slows to a crawl with files > 100 MB. | https://git-lfs.github.com/ |
| **Makefile** | A file that holds named commands (`make reproduce`, `make thesis`). Saves you from memorizing long shell commands. | [docs/GLOSSARY.md](../docs/GLOSSARY.md) |
| **pyproject.toml** | Modern Python's replacement for `setup.py` and `requirements.txt`. Lists dependencies + project metadata. | https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ |

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| `pdflatex` errors on `\usepackage{biblatex}` | MiKTeX asks to install `biblatex` during first run; click Install. If headless, run `mpm --install=biblatex` |
| "git lfs" not found | Install: `git lfs install` after installing the Git LFS extension from https://git-lfs.com |
| Claude stops halfway | Paste: "Continue T02 from where you left off. Skip anything already done." |

---

## ➡️ When done

```
python scripts/mark_done.py T02
python scripts/next.py
```
