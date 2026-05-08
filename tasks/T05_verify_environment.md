# T05 — Verify the Environment (End-to-End Smoke Test)

**Phase 1 · Setup · Estimated time: 10 minutes · Owner: anyone**

---

## 🎯 What you are doing
Running a tiny end-to-end sanity test: take a 30-second sample video, transcribe it, embed its sentences, and print the result. If this works, our whole pipeline will work later.

## 🤔 Why
Catch environment problems **now**, while they are still cheap to fix, rather than during a 30-video overnight run.

## ✅ How to know you are done
- `python scripts/smoke_test.py` exits with "✅ All checks passed."

---

## 📝 Steps

### Step 1 — Ask Claude to build the smoke test

Prompt:

> Execute task T05 from `tasks/T05_verify_environment.md`. Write `scripts/smoke_test.py` that does the following checks, each with a `[PASS]` or `[FAIL]` print line. Exit 1 if any fail.
> 1. Import torch, transformers, sentence_transformers, faster_whisper, segeval, librosa.
> 2. Download a 30-second sample audio clip (use https://github.com/SYSTRAN/faster-whisper/raw/master/tests/data/jfk.flac — it ships with faster-whisper tests).
> 3. Transcribe with faster-whisper tiny.en model (downloads the first time, ~40 MB).
> 4. Encode the sentences with all-MiniLM-L6-v2.
> 5. Compute cosine similarity between sentence pairs.
> 6. Call the Ollama llama3.1:8b model with a trivial prompt; verify response is non-empty.
> 7. Verify ffmpeg is callable via `subprocess.run`.
> 8. Verify pdflatex is callable.
> Print total runtime.

### Step 2 — Run it

```
python scripts/smoke_test.py
```

Expected output (will take 2–5 minutes the first time because of model downloads):
```
[PASS] Python 3.11.x
[PASS] torch 2.x (device: cuda / cpu)
[PASS] transformers imported
[PASS] sentence_transformers imported
[PASS] faster_whisper imported
[PASS] segeval imported
[PASS] ffmpeg available
[PASS] pdflatex available
[PASS] Downloaded sample audio (jfk.flac, 352 KB)
[PASS] Transcribed: "And so my fellow Americans, ask not what your country..."
[PASS] SBERT embedding shape = (N, 384)
[PASS] Ollama llama3.1:8b responds
Total: 185.3s
✅ All checks passed.
```

### Step 3 — If anything fails

Look at the `[FAIL]` line. It tells you which dependency is broken. Most common fixes are in the table below. Once fixed, rerun.

---

## 🆘 Troubleshooting

| FAIL line | Fix |
|---|---|
| `torch` | Go back to T03. Reinstall torch. |
| `faster_whisper` | Go back to T03. |
| `ffmpeg` | Go back to T01. FFmpeg is not on PATH. |
| `pdflatex` | Go back to T01. MiKTeX/MacTeX not installed. |
| `ollama` — connection refused | Ollama server is not running. Start it (T04 step 2). |
| `ollama` — model not found | Pull the model: `ollama pull llama3.1:8b`. |
| Download fails | Check internet. Some campus networks block GitHub LFS — try your phone hotspot as a test. |

---

## ➡️ When done

```
python scripts/mark_done.py T05
python scripts/next.py
```

🎉 Congrats — Phase 1 is complete. From T06 onwards we stop installing and start doing research.
