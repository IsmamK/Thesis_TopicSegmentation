# 🤝 COLLABORATION — How the 5 of Us Work Together

**Read this once when you join the project. Re-read whenever a hand-off feels confusing.**

---

## The team & default ownership

| ID | Name | Default ownership |
|---|---|---|
| ismam | Ismam Khan | Lead, novel-method modules (T25–T28), final integration |
| fahmida | Fahmida Afrin Moon | Dataset curation + annotation (T09–T12, T42) |
| shahriar | Shahriar Islam Rafi | Baselines + evaluation + statistics (T13, T22–T24, T29, T30) |
| alimool | Alimool Razi | Preprocessing + demo (T14–T18, T39) |
| sadia | Sadia Alam | Writing — thesis, paper, poster, slides (T32–T38, T40, T41, T45, T31) |
| (supervisor) | Mr. Annajiat Alim Rasel | Reviews + sign-offs |

This is a default, not a wall. Anyone can claim any task that's free.

---

## The golden flow

```
   Open terminal in project folder
            │
            ▼
   .\.venv\Scripts\activate           (Windows; or: source .venv/bin/activate)
            │
            ▼
   python scripts/today.py           ← shows progress + next task
            │
            ▼
   python scripts/claim.py T<NN> <yourname>   ← so the team sees you're on it
            │
            ▼
   Read tasks/T<NN>_*.md (full instructions)
            │
            ▼
   Do the task (with or without Claude)
            │
            ▼
   git add . && git commit -m "T<NN>: <verb> <what>"
            │
            ▼
   python scripts/mark_done.py T<NN>
            │
            ▼
   python scripts/today.py           ← see what's next
```

---

## Branching & commits

We work on a single `main` branch. **One commit per task.** Commit message format:

```
T<NN>: <imperative verb> <what>

Optional longer description.
```

Examples:
```
T14: transcribe all 30 videos with Whisper large-v3
T25: implement reliability-weighted fusion module
```

Push at the end of each task so others can pull.

If a task is huge (e.g., T29 ablations), branch off:

```
git checkout -b feature/T29-ablations
# ...do work...
git push -u origin feature/T29-ablations
# open a PR on GitHub, request review, merge to main when green
```

---

## Hand-off rules — when one person finishes a task and the next starts

1. **The finisher** runs `python scripts/mark_done.py T<NN>`. The script auto-regenerates `STATUS.md` and `NEXT.md`.
2. **The finisher** writes a 2-line note in the commit message: any quirks the next person should know.
3. **The finisher** commits + pushes. **No work in progress is left uncommitted.**
4. **The starter** pulls (`git pull`), runs `python scripts/today.py`, and follows the next task file from the top.

If the starter is confused: run `python scripts/context.py` and paste it into a Claude chat (or share with the team). It produces a self-contained context block.

---

## Daily routine (every team member, every working day)

1. `git pull`
2. `.\.venv\Scripts\activate`
3. `python scripts/today.py`
4. Pick a task that's `todo` and free → `python scripts/claim.py T<NN> <yourname>`
5. Work. Commit when done.
6. `python scripts/mark_done.py T<NN>` and push.

---

## How to communicate

- **Code & data:** Git + GitHub.
- **Quick questions / co-ordination:** team chat (Discord/WhatsApp).
- **Decisions that affect the thesis or the timeline:** add a row to `docs/DECISION_LOG.md` (create it on first need) and announce in chat.
- **Blocked tasks:** `python scripts/mark_progress.py T<NN> blocked "specific reason"` and post in chat.

---

## Code review

For non-trivial commits (> 50 LOC), open a PR. One team-mate reviews and squash-merges.
For tiny commits (typos, README tweaks), push to main directly.

Review checklist:
- [ ] Does it match the task file?
- [ ] Are there tests for new logic?
- [ ] Does it touch `docs/`? If yes, voice is passive/we, no AI mention.
- [ ] Does it add a dependency? If yes, `pyproject.toml` updated.

---

## What happens if two of us start the same task

`progress.yaml` stores the `owner` field. When you `claim.py`, it sets `owner` and flips status to `doing`. If someone else has already claimed it, the script warns you. **Always** run `claim.py` before you start coding.

---

## Conflict resolution

- **Coding-style conflict:** `ruff check --fix .` and `black .` decide.
- **Methodology disagreement:** add a row to `docs/DECISION_LOG.md`, raise with the supervisor at next sync.
- **Numbers don't match between two scripts:** the task with the more recent timestamp in `results/` wins, but log the discrepancy.

---

## When a new person joins

Hand them `START_HERE.md`. After they finish T01, point them at `docs/HANDOFF.md` for a 5-minute orientation. Then they run `python scripts/today.py` and pick a `todo` task.
