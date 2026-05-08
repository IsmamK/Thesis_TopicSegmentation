# T14 — Transcribe All Videos (Whisper large-v3)

**Phase 4 · Preprocessing · Estimated time: 30 min setup + 4–8 h unattended transcription · Owner: Alimool (GPU required, or overnight on CPU)**

---

## 🎯 What you are doing
Running OpenAI's Whisper model on every video's audio track, producing a time-stamped transcript (which word was said at which second). This transcript feeds every downstream text-based module.

## 🤔 Why
Whisper large-v3 is the best open ASR (Automatic Speech Recognition) model publicly available. Its word-level timestamps let us align text boundaries back to video time.

## ✅ How to know you are done
- `data/whisper/<video_id>.json` exists for all 30 videos, each with word-level timestamps.
- `data/whisper/summary.csv` lists WER proxy (no GT) + transcript length per video.
- A random sample of 3 transcripts sounds correct when you eye-read them against the video.

---

## 📝 Steps

### Step 1 — GPU setup (optional but 10× faster)

**If you have an NVIDIA GPU on Windows:**
1. Install NVIDIA driver (latest): https://www.nvidia.com/drivers/
2. Install CUDA 12.1 runtime: https://developer.nvidia.com/cuda-12-1-0-download-archive
3. Reinstall torch with GPU support:
   ```
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
4. Verify: `python -c "import torch; print(torch.cuda.is_available())"` should print `True`.

**If on CPU only**: it still works, it is just slower — 4–5× real-time. 20 h of video → ~80 h of compute → leave it running for 3 nights.

**No GPU, tight on time?** Use the `medium` model instead of `large-v3` (2× faster, slightly less accurate).

### Step 2 — Ask Claude

> Execute T14. Write `src/lecseg/preprocess/transcribe.py` and `scripts/transcribe_all.py`.
>
> Use `faster-whisper` (CTranslate2-optimised) with model=`large-v3`, beam_size=5, word_timestamps=True, vad_filter=True. Auto-detect GPU (fp16) vs CPU (int8).
>
> For each video in `data/manifest.jsonl`:
> 1. Check if `data/whisper/<video_id>.json` exists → skip (idempotent).
> 2. Feed `data/raw/<video_id>/audio.wav` to the model.
> 3. Save JSON with fields: `language`, `segments` (list of {start, end, text, words:[{start,end,word,prob}]}).
> 4. Append WER proxy to `data/whisper/summary.csv` (use average segment probability as a crude confidence).
>
> Log progress with rich.progress.
>
> After all done, run a quick sanity check: print total transcribed seconds vs total audio seconds; they should match within 1%.

### Step 3 — Run it

```
python scripts/transcribe_all.py
```

It may print: `Running on device: cuda (fp16)`  or  `Running on device: cpu (int8)`.

### Step 4 — Eye-check 3 transcripts

Open 3 random `.json` files. Check that the first 20 sentences match the video's opening 2 minutes. Small errors (Newton → Newtown, Pythagoras → Pythagor us) are normal; whole-sentence hallucinations are not.

If a whole sentence is gibberish, re-run with `vad_filter=False` or try the `medium` model instead.

---

## 🧠 Concepts

| Term | Plain-English meaning |
|---|---|
| **ASR** | Automatic Speech Recognition — turning audio into text. |
| **Whisper** | OpenAI's multilingual ASR model, released 2022, open-source. |
| **faster-whisper** | A re-implementation of Whisper that's ~4× faster using CTranslate2. Same quality. |
| **WER** | Word Error Rate. % of words transcribed wrong. We don't have GT text so we use confidence score as a proxy. |
| **VAD** | Voice Activity Detection. Skips silent sections to save compute. |
| **fp16 / int8** | Numeric precision. fp16 is fast on GPU; int8 is fast on CPU. |

More: [docs/CONCEPTS.md#asr](../docs/CONCEPTS.md#asr)

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| "No CUDA devices" | You don't have a GPU or drivers are missing. Falls back to CPU automatically. |
| Out of memory on GPU | Reduce `beam_size` from 5 to 1, or use the `medium` model. |
| A transcript is gibberish | The audio is too quiet or music-heavy. Normalize: `ffmpeg -i audio.wav -filter:a loudnorm audio_norm.wav`. |
| Takes forever on CPU | Use `tiny.en` model as a debug-only cheap pass; use `large-v3` only overnight. |

---

## ➡️ When done

```
python scripts/mark_done.py T14
python scripts/today.py
```
