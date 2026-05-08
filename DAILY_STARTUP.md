# 🌅 DAILY STARTUP — Read once, do every day

**This is the static reference. The live version is `python scripts/today.py`.**

---

## The 60-second routine

```
.\.venv\Scripts\activate          # Windows  (or: source .venv/bin/activate)
git pull                          # 1. sync with team
python scripts/today.py           # 2. see progress + next task
```

`today.py` will tell you:
- Overall progress (% done out of 47).
- Per-phase progress bars.
- The exact next task and its file path.
- The 3 commands you need (read / claim / mark-done).

---

## Picking the next task

If `today.py` shows multiple tasks ready, pick by:

1. **What's already claimed** — don't grab someone else's `🟡 doing` task.
2. **Your skill** — see `docs/COLLABORATION.md` for who-does-what.
3. **Phase order** — earlier phase tasks unblock later ones.

When you've decided:

```
python scripts/claim.py T<NN> <yourname>
python scripts/show.py  T<NN>     # prints the task file
```

---

## While you work

- Commit small, commit often (`git commit -m "T<NN>: <what>"`).
- If a step takes more than 30 minutes longer than the task expects → `python scripts/mark_progress.py T<NN> blocked "reason"` and ask in chat.
- Update the relevant thesis section as you go (T32–T37 expect content from earlier tasks). See `docs/THESIS_WRITING_GUIDE.md`.

---

## Finishing a task

```
python scripts/mark_done.py T<NN>
git add -A && git commit -m "T<NN>: complete"
git push
```

`mark_done.py` regenerates `STATUS.md` and `NEXT.md`. The next person who runs `today.py` will see the updated state.

---

## Resuming a Claude session

```
python scripts/context.py > context.txt
```

Open `context.txt`, copy everything, paste into a fresh Claude chat. Claude resumes with full context.

---

## When something breaks

1. `docs/TROUBLESHOOTING.md` — top-5 panic fixes solve 80 % of issues.
2. `python scripts/context.py` → paste to Claude with the exact error.
3. Team chat: include task ID + the exact command + the full error.

---

## Common commands cheat-sheet

| Goal | Command |
|---|---|
| 👋 Daily dashboard | `python scripts/today.py` |
| 📊 HTML dashboard | `python scripts/visualize_progress.py` |
| 📖 Read a task | `python scripts/show.py T<NN>` |
| 🙋 Claim | `python scripts/claim.py T<NN> <name>` |
| ✅ Done | `python scripts/mark_done.py T<NN>` |
| 🚫 Block | `python scripts/mark_progress.py T<NN> blocked "<reason>"` |
| 💬 Claude resume | `python scripts/context.py` |
| 📝 Add a paper | `python scripts/add_paper.py "<url>"` |
| 🔬 Interpret an output | `python scripts/interpret.py <file>` |
| 🛠️ Build thesis | `make thesis` |
| 🌐 Run web demo | `make webapp` |
| 🎓 Pre-defense check | `make check` |

Print this once and pin it next to your monitor.
