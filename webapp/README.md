# LECSEG Streamlit Web App

Built in **T39**. Run locally with:

```powershell
make webapp
# or
streamlit run webapp/app.py
```

Then open http://localhost:8501.

## What it does

The app now has two workflows.

### 1. Segment any YouTube lecture

This is the product/demo mode. A user can paste a YouTube URL or video ID and generate chapter timestamps.

Pipeline used:

```text
YouTube video
-> public captions if available
-> Whisper fallback if enabled and yt-dlp/FFmpeg are installed
-> sentence splitting
-> text embeddings
-> LecSeg boundary prediction
-> generated chapter timestamps
-> JSON / YouTube timestamp export
```

The app can cache arbitrary videos under:

```text
data/webapp_cache/<video_id>/
```

Cached files include metadata, transcript, sentence splits, and embeddings. This makes repeated demos much faster.

### 2. Benchmark LecSeg-30

This is the research mode. It uses the existing benchmark assets and creator-provided reference chapters, so it can report:

- Pk;
- WindowDiff;
- F1@2;
- tolerance-F1;
- visual boundary timelines;
- dataset-level modern diagnostic metrics.

## Important limitations

- For arbitrary videos, the app can generate chapters even without creator reference chapters.
- Pk, WindowDiff, and F1 require a reference chapter file, so they are only shown in benchmark mode or when references exist.
- Public captions are much faster than Whisper. Whisper fallback can be slow and requires `yt-dlp`, FFmpeg, and enough local compute.
- The arbitrary-video path currently uses text-based LecSeg boundary prediction. Visual/prosody/OCR signals still require the heavier offline preprocessing pipeline.

## Hosting

For supervisor or panel access, deploy the repository to a machine that includes the cached `data/` assets and Python dependencies, then run:

```powershell
streamlit run webapp/app.py --server.port 8501
```

For a reliable live demo, pre-cache a few selected videos with the app before the presentation.

## Privacy

The app does not call paid APIs. It reads YouTube captions directly when available, optionally downloads audio for local Whisper fallback, and stores cached demo assets locally under `data/webapp_cache/`.
