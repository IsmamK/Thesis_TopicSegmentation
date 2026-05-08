# T10 — Download Videos, Audio, and Chapter Metadata

**Phase 3 · Dataset · Estimated time: 30 min setup + 3–6 hours unattended download · Owner: Fahmida + Alimool**

---

## 🎯 What you are doing
Running yt-dlp to download all 30 videos, extract their audio tracks, and save the chapter metadata. The files go onto an external SSD (NOT committed to Git).

## 🤔 Why
Videos can be 2–5 GB each. You cannot run Whisper on them until they are local.

## ✅ How to know you are done
- `data/raw/<video_id>/video.mp4` exists for all 30.
- `data/raw/<video_id>/audio.wav` exists (mono, 16kHz) for all 30.
- `data/raw/<video_id>/info.json` exists with chapter timestamps.
- `data/manifest.jsonl` has 30 lines.

---

## 📝 Steps

### Step 1 — Plug in an external SSD with ≥ 200 GB free

Create a symlink so `data/raw/` points to the SSD (keeps the project folder small):

**Windows (run terminal as Administrator):**
```
rmdir data\raw 2>nul
mklink /D data\raw "E:\lecseg_videos"
```

**Mac / Linux:**
```
rm -rf data/raw
ln -s /Volumes/SSD/lecseg_videos data/raw
mkdir -p data/raw
```

### Step 2 — Ask Claude

> Execute T10. Write `src/lecseg/data/youtube.py` and `scripts/download_all.py`. Read `data/video_list.csv`, and for each row:
> 1. Use yt-dlp to download the video (MP4) + info.json with `--write-info-json`
> 2. Extract audio with ffmpeg: mono, 16kHz, WAV
> 3. Save outputs to `data/raw/<video_id>/`
> 4. Append a line to `data/manifest.jsonl` with keys: id, domain, duration_sec, path, num_chapters
> Use `concurrent.futures` with max 3 parallel downloads (polite throttling for YouTube). Log progress with rich.progress. Idempotent: skip videos already downloaded.

### Step 3 — Run it

```
python scripts/download_all.py
```

This will take **3–6 hours** depending on internet. Leave it running. Check back occasionally.

### Step 4 — Verify

```
python -c "import json; lines = open('data/manifest.jsonl').readlines(); print(f'{len(lines)} videos, total {sum(json.loads(l)[\"duration_sec\"] for l in lines)/3600:.1f}h')"
```

Should print `30 videos, total 20.X h` or similar.

---

## 🧠 Concepts

| Term | Meaning |
|---|---|
| **Symlink** | A folder that is really a pointer to another folder. Lets us keep code on the internal drive but big data on external. |
| **Manifest** | A machine-readable index of our dataset. Every pipeline stage reads `manifest.jsonl` to know which videos exist. |
| **yt-dlp** | Command-line YouTube downloader. Maintained fork of youtube-dl with better speed + fewer bugs. |

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| "Video unavailable" | YouTube region-locked it. Replace with a similar video from another channel. |
| Download too slow | Campus Wi-Fi limits throughput. Try overnight or use phone hotspot. |
| Disk fills up | Each video + audio ≈ 3 GB. 30 videos = ~90 GB. Ensure SSD has 200 GB free. |
| yt-dlp breaks | YouTube API changes often. Update: `pip install -U yt-dlp`. |

---

## ➡️ When done
```
python scripts/mark_done.py T10
python scripts/next.py
```
