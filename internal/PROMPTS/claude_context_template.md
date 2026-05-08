# Starter prompt for every new Claude session on this project

Paste this block (or the output of `python scripts/context.py`) as the very first message in a new Claude chat.

```
I am continuing work on my undergraduate thesis project LECSEG
(Lecture Video Topic Segmentation).

Before doing anything, please read (in this order):

  1. internal/CLAUDE.md          — house rules. Non-negotiable.
  2. progress.yaml               — ground truth for task status.
  3. docs/NOVELTY_TRACKER.md     — our 7 novelty claims (N1–N7).
  4. docs/METHODOLOGY.md         — the research plan.
  5. The specific task file      — tasks/T<NN>_*.md — for whatever we do now.

Rules to always follow (from internal/CLAUDE.md):
  - Do NOT hallucinate results or numbers. If unknown, write TBD.
  - Do NOT mark tasks done yourself (I run scripts/mark_done.py).
  - Docs in docs/ are read by teachers — never mention AI, Claude, LLM, or prompts there.
  - Progress tracking is done ONLY through scripts/*.py, not by editing progress.yaml.
  - Scripts must be idempotent and log progress.

Run `python scripts/today.py` from the terminal for the live project state.

Your job for this session: __________
```

Fill in "Your job for this session" with what you want to do now (usually "execute T<NN>").
