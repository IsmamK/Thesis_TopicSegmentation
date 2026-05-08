# Claude House Rules — READ FIRST

**This file is read by Claude at the start of every session. Every rule here is non-negotiable.**
**This folder (`internal/`) is removed before thesis submission.**

---

## Identity of the project

- **Name:** LECSEG (Lecture Video Topic Segmentation)
- **Thesis group:** T2520718, BracU, CSE400 Final Thesis
- **Supervisor:** Mr. Annajiat Alim Rasel
- **Goal:** Build an open, reproducible, hierarchical multimodal system that splits lecture videos into topic chapters with chapter-level + subtopic-level granularity.
- **7 novelty claims (N1–N7):** see [`docs/NOVELTY_TRACKER.md`](../docs/NOVELTY_TRACKER.md)

## The golden rule: READ BEFORE YOU WRITE

Before doing anything, in order:

1. Read `internal/CLAUDE.md` (this file).
2. Read `progress.yaml`.
3. Read the specific `tasks/T<NN>_*.md` for the task at hand.
4. Read `docs/METHODOLOGY.md` if the task touches research decisions.
5. Read `docs/NOVELTY_TRACKER.md` before touching any module that implements a novelty claim.
6. If the task involves papers: read `docs/LITERATURE_MATRIX.md`.

If any of these are missing, **stop and ask the user**. Do not invent them.

## Hard rules

1. **Never hallucinate a result.** If you did not compute or read a number, do not write one. Write `TBD` and surface it.
2. **Never overwrite the user's manual edits silently.** If a file has non-generated content, ask before touching it.
3. **Never mark a task done yourself.** Only the user runs `scripts/mark_done.py`.
4. **Never commit `.env`, `data/raw/`, `.venv/`, large model files, or anything in `internal/`** unless explicitly asked.
5. **Every script must be idempotent.** Re-running it must not duplicate or corrupt data.
6. **Every script must log progress** using `rich.progress` or `tqdm`. No silent 30-minute runs.
7. **Every experiment writes its config and git-SHA** into the results folder next to the numbers. This is how reproducibility works.
8. **All file paths are relative to the project root.** No absolute paths in source.
9. **Do not introduce new dependencies** without updating `pyproject.toml` and noting it in the task's PR.
10. **Do not split a PR across multiple tasks.** One PR = one task = one row in `progress.yaml`.

## Writing style

- Plain English. Assume a non-technical reader.
- Every new term is linked to `docs/GLOSSARY.md` on first use.
- Every module has a docstring explaining *why* it exists, not just *what* it does.
- Every file the user sees includes a "how to know you are done" checklist.

## Separation of public vs. internal

Two parallel folders:

- **`docs/`** — PUBLIC. Written as if a teacher or external reader is the audience. **Never mention "Claude", "AI", "LLM-generated", "prompt" here.** Written in the passive/collective voice: "we implement…", "we evaluate…".
- **`internal/`** — PRIVATE. Everything about how Claude was used, prompts, playbooks. This whole folder is stripped before submission by running `scripts/strip_internal.py`.

When editing a doc, check which folder it lives in and match the voice.

## Subagent rules

When the task is large (>5 file operations):

- Use the **Explore** subagent to find files and read them, to keep the main context window clean.
- Use the **Plan** subagent before writing novel code.
- Batch independent work into parallel `Agent()` calls.

## When you hit a question

- If the user has not specified and the answer is non-obvious, **ask**, do not guess.
- If the answer is obvious from `docs/METHODOLOGY.md` or a task file, follow that, then note your decision in the PR description.

## When you finish

- Print a one-line diff summary.
- Remind the user to run `python scripts/mark_done.py T<NN>` (do not run it yourself).
- Remind them to run `python scripts/update_thesis.py T<NN>` if the task produced a number/figure that goes into the thesis.

## Deliverables that must exist by submission

See `progress.yaml` for the full task list. High level:

- `thesis/main.pdf` — the thesis
- `paper/ieee.pdf` — the 8-page paper
- `webapp/` — Streamlit demo
- `data/release/` — LECSEG-30 dataset
- `results/` — all tables & figures
- `docs/DEFENSE_QA.md` — 50+ Q&A pairs
- `slides/defense.pdf` — slide deck
- `poster/poster.pdf` — A1 poster
