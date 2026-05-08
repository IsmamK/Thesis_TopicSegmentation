# 👋 Start Here — First-time Setup

**You are here because you just opened this project for the first time.**
Do the 4 steps below, in order. **You can skip the ones you already have installed.**

Expected time: **30–45 minutes** if nothing is installed yet.

---

## Step 0 — Know what this is

This is a final-year thesis project. We are building a system that automatically
splits long lecture videos into topic chapters. See [`README.md`](README.md) for
the big picture. If you don't understand a word you read anywhere in the project,
look it up in [`docs/GLOSSARY.md`](docs/GLOSSARY.md) — every technical term is explained there.

---

## Step 1 — Install the basic tools

You need **6 things** on your computer. Install them in this order:

### 1.1 Git (version control)
- **Windows:** download from https://git-scm.com/download/win → run installer → keep all defaults → restart terminal.
- **Mac:** open Terminal, run `xcode-select --install`
- **Check it works:** open a new terminal and run `git --version`. Should print something like `git version 2.45.0`.

### 1.2 Python 3.11 (the language we use)
- **Windows:** download Python 3.11.9 from https://www.python.org/downloads/windows/ → run installer → **TICK "Add Python to PATH"** at the bottom of the installer → click Install Now.
- **Mac:** `brew install python@3.11`
- **Check:** `python --version` should print `Python 3.11.x`. If it says a different version, try `python3.11 --version`.

⚠️ **Important:** we use Python **3.11**, not 3.12 or 3.13. Some libraries we need are not ready for newer versions yet.

### 1.3 FFmpeg (for video + audio processing)
- **Windows:** download the "essentials" zip from https://www.gyan.dev/ffmpeg/builds/ → extract to `C:\ffmpeg` → add `C:\ffmpeg\bin` to your PATH. Guide with pictures: https://phoenixnap.com/kb/ffmpeg-windows
- **Mac:** `brew install ffmpeg`
- **Check:** `ffmpeg -version` should print a version number.

### 1.4 VS Code (the code editor)
- Download from https://code.visualstudio.com/ and install.
- After install, open VS Code. Press `Ctrl+Shift+X` (Windows) / `Cmd+Shift+X` (Mac) and install these extensions:
  - **Python** (by Microsoft)
  - **LaTeX Workshop** (by James Yu) — used later for the thesis
  - **GitLens** (by GitKraken) — makes Git easier
  - **Markdown All in One** (by Yu Zhang)

### 1.5 A LaTeX distribution (for the thesis PDF)
- **Windows:** install MiKTeX from https://miktex.org/download — run the installer → during install, when it asks "Install missing packages on the fly", select **Yes**.
- **Mac:** install MacTeX from https://www.tug.org/mactex/ (big download, be patient).
- **Check:** in a new terminal, `pdflatex --version` should print a version number.

### 1.6 (Optional but recommended) yt-dlp (for downloading YouTube videos)
- In a terminal: `pip install yt-dlp`
- Check: `yt-dlp --version`.

---

## Step 2 — Get the project onto your computer

If you are the first person setting up:

```
cd C:\Users\YourName\Documents
git clone <URL-of-our-GitHub-repo>.git lecseg
cd lecseg
```

If the project is already on a shared drive, just open a terminal in that folder.

**VS Code shortcut:** open VS Code, click `File → Open Folder…` and select the project folder.

---

## Step 3 — Set up the Python environment

A "virtual environment" is a folder that holds all the Python libraries this
project needs, so they don't mix with other projects on your computer.
Create it **once**. Activate it **every time** you open a new terminal.

Run in the project folder:

```
python -m venv .venv
```

Then **activate** it:

```
# Windows (PowerShell or Command Prompt)
.\.venv\Scripts\activate

# Mac / Linux / Git Bash on Windows
source .venv/bin/activate
```

You will know it worked because your prompt now starts with `(.venv)`.

Now install the basic tools the project scripts need (the heavy ML libraries come later):

```
pip install pyyaml rich typer
```

---

## Step 4 — See the dashboard

Now run:

```
python scripts/dashboard.py
```

You should see a colorful progress bar and a list of tasks.
**If the dashboard printed something → you are set up correctly. Celebrate.** 🎉

Then run:

```
python scripts/next.py
```

This tells you the **next task to do**. Follow it. It will open a file in
`tasks/` that walks you through what to do.

---

## 💡 From now on, forever, every day

When you start work, do these 3 things:

1. Open a terminal in the project folder.
2. Activate the environment: `.\.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Mac).
3. Run `python scripts/next.py`.

That is it. The script will tell you what to do.

---

## 😬 Something broke

Read [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).
The 5 most common problems are listed at the top with copy-paste fixes.

---

## 📚 I want to learn the concepts

Open [`docs/CONCEPTS.md`](docs/CONCEPTS.md). It explains every topic this thesis
touches — what is "topic segmentation", what is an "embedding", what is "Pk" — in
plain English with links to free tutorials.

If a word in any file is unfamiliar, the fastest way to understand it is to
search for it in [`docs/GLOSSARY.md`](docs/GLOSSARY.md).
