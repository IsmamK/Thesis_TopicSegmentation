# T01 — Install Prerequisites

**Phase 1 · Setup · Estimated time: 30–45 minutes · Owner: anyone, once per person**

---

## 🎯 What you are doing
Installing the software tools that every other task depends on: Python, Git, FFmpeg, LaTeX, VS Code.

## 🤔 Why
None of our scripts, models, or the thesis PDF can be built without these.

## ✅ How to know you are done
When you can run all 4 of these commands in a fresh terminal and get a version number back:
```
python --version
git --version
ffmpeg -version
pdflatex --version
```

---

## 📝 Steps

Go through [START_HERE.md](../START_HERE.md) **Step 1** and install all 6 items in this order:

1. **Git** — https://git-scm.com/download/win (Windows) or `xcode-select --install` (Mac)
2. **Python 3.11** — https://www.python.org/downloads/windows/ — **tick "Add Python to PATH"** during install
3. **FFmpeg** — https://www.gyan.dev/ffmpeg/builds/ → download "essentials" zip → extract to `C:\ffmpeg` → add `C:\ffmpeg\bin` to PATH
4. **VS Code** — https://code.visualstudio.com/ → install the 4 extensions listed in START_HERE.md
5. **MiKTeX (LaTeX on Windows)** — https://miktex.org/download → during install: **Install missing packages on the fly → Yes**
6. **yt-dlp** — `pip install yt-dlp`

### Windows PATH — how to add a folder to PATH (for FFmpeg)
1. Press `Win` key → type "environment variables" → open "Edit the system environment variables".
2. Click `Environment Variables…`.
3. In the lower section ("System variables"), scroll to `Path` → click `Edit…`.
4. Click `New` → paste `C:\ffmpeg\bin` → click OK → OK → OK.
5. **Close and reopen every terminal** so the change takes effect.

---

## ✅ Verify it works

Open a **new** terminal (important: the one you had open before won't see the changes).
Run these commands. Every one should print a version number:

```
python --version
git --version
ffmpeg -version
pdflatex --version
yt-dlp --version
```

If any of them say "command not found" or "'xxx' is not recognized":
- You skipped the "Add to PATH" step during install.
- Re-run that installer, or manually add the folder to PATH (see above).

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| `python --version` says Python 3.12 | You have an older Python installed. Install 3.11 specifically. You can have multiple versions side-by-side. |
| `pdflatex: command not found` on Mac | After MacTeX install, close/reopen Terminal, then `eval "$(/usr/libexec/path_helper)"` |
| Anti-virus blocks MiKTeX | Temporarily disable it during install, re-enable after |
| FFmpeg zip extracts strangely | The zip nests one folder deep. Make sure the final path is `C:\ffmpeg\bin\ffmpeg.exe`, not `C:\ffmpeg\ffmpeg-6.1\bin\ffmpeg.exe`. Move files up one level if needed. |

For more help: [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md)

---

## ➡️ When done

Mark this task done and see the next one:

```
python scripts/mark_done.py T01
python scripts/next.py
```
