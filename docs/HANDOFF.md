# 🔁 HANDOFF — When a Different Person Picks Up the Project

**Read this in 5 minutes. You'll know exactly where we are and what to do next.**

---

## You just opened the project. Now what?

### 1. Make sure you can run things

```
.\.venv\Scripts\activate              # Windows  (or: source .venv/bin/activate)
python scripts/today.py
```

If `today.py` shows the dashboard → great, you are set up.
If it errors → you are new. Open `START_HERE.md` and do T01–T05 first.

### 2. Sync with the team

```
git pull
```

Always pull before starting. Always push when finishing.

### 3. See what's done & what's next

`python scripts/today.py` shows a colourful dashboard:
- Overall progress bar.
- Per-phase progress bars.
- The exact next task (with the file path to read).
- The 3 commands you need: read the task, work on it, mark it done.

### 4. Want a richer view?

```
python scripts/visualize_progress.py
```

Opens an HTML dashboard in your browser with every task colour-coded.

### 5. Continuing a Claude session?

```
python scripts/context.py > context.txt
```

Open the file, copy everything, paste into a new Claude chat. Claude will know where we are.

---

## What if I'm picking up MID-task that someone else started?

1. Run `python scripts/today.py`. The status will show which task is `🟡 doing` and who claimed it.
2. Message that person on the team chat: "I'm taking over T<NN>." Wait for ack.
3. Once they ack:
   ```
   python scripts/claim.py T<NN> <yourname>
   ```
4. Read the task file: `python scripts/show.py T<NN>`.
5. Read the latest commit message and the diff:
   ```
   git log -1 --stat
   git diff HEAD~1
   ```
6. Continue from where they stopped. Their commit messages should describe state.

---

## Quick map

| Want to… | Run / open |
|---|---|
| See progress and what to do | `python scripts/today.py` |
| Read a specific task | `python scripts/show.py T<NN>` |
| Claim a task | `python scripts/claim.py T<NN> <yourname>` |
| Mark a task done | `python scripts/mark_done.py T<NN>` |
| Block a task | `python scripts/mark_progress.py T<NN> blocked "reason"` |
| Get Claude context | `python scripts/context.py` |
| HTML dashboard | `python scripts/visualize_progress.py` |
| Add a paper | `python scripts/add_paper.py "<url>"` |
| Final check | `python scripts/pre_defense_check.py` |

---

## Where things live

| You want to… | File / folder |
|---|---|
| Understand a concept | `docs/CONCEPTS.md` |
| Look up a word | `docs/GLOSSARY.md` |
| Fix an error | `docs/TROUBLESHOOTING.md` |
| Read the research plan | `docs/METHODOLOGY.md` |
| Read our 7 novelties | `docs/NOVELTY_TRACKER.md` |
| Read team rules | `docs/COLLABORATION.md` |
| Interpret an output file | `docs/OUTPUT_INTERPRETATION.md` |
| Prep for the defense | `docs/DEFENSE_PREP.md` |
| Add a paper | `docs/PAPER_ADDITION_GUIDE.md` |
| Detailed env setup | `docs/SETUP.md` |
| External learning links | `docs/RESOURCES.md` |
| The full task list | `tasks/` |
| The current state | `progress.yaml`, `STATUS.md`, `NEXT.md` |
| What we're doing (public-facing) | `WHAT_WE_ARE_DOING.md` |
| The visual map | `PROJECT_MAP.md` |

---

## What you should NOT do without asking

- Edit `progress.yaml` by hand (use `scripts/*.py` instead).
- Push to `main` if a CI check is red.
- Force-push.
- Add a heavy dependency without updating `pyproject.toml` and pinging the team.
- Move files between folders (breaks every script that uses paths).

---

## When you're stuck

1. `docs/TROUBLESHOOTING.md` — the top 5 fixes solve 80 % of issues.
2. `python scripts/context.py` → paste to Claude with your error.
3. Team chat with: task ID + exact command + full error.
