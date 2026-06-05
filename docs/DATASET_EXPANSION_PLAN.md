# LECSEG-30 Dataset Expansion Plan

Target: expand from 30 to 40+ videos for LECSEG-40.

## Current status
- 30 videos, 32.52 hours, 5 domains
- Distribution: Biology 6, CS 7, Math 4, Philosophy 6, Physics 7
- **Math is underrepresented (4 videos → selector performs worst there)**

## Priority: Add 4 Math videos to reach Math=8 (matching CS/Physics)
This directly addresses the Math domain failure identified in the ablation study.

## Verified candidates (checked with yt-dlp for chapters + duration)

| Video ID | Title | Domain | Duration | Chapters | Status |
|---|---|---|---|---|---|
| QFu5nuc-S0s | Stanford CS229 Lec 18 - Continuous State MDP | CS | 80 min | 9 | ✓ verified |

## Unverified candidates to check

Run: `python scripts/find_candidate_videos.py --check <video_id>`

### Math (priority — need 4+ more)
- MIT 18.01 Single Variable Calculus lectures (look for individual lectures with chapters)
- MIT 18.02 Multivariable Calculus
- MIT 18.06 Linear Algebra (Gilbert Strang) — some have chapters
- 3Blue1Brown long-form lectures
- Harvard Abstract Algebra lectures

### CS (optional — already have 7)
- MIT 6.034 AI lectures
- Stanford CS231n CNN lectures (look for ones with chapters)
- CS50 Harvard lectures

### Physics (optional — already have 7)
- More MIT 8.xxx physics lectures
- Leonard Susskind Stanford lectures

### Biology (need 1-2 more to balance)
- iBiology lectures
- MIT 7.xxx biology lectures

### New domain: Chemistry (would add diversity)
- MIT 5.111 Principles of Chemical Science
- Organic Chemistry Tutor (if has chapters)

## Process to add new videos

1. Find video ID and verify it has ≥4 chapters and is ≥30 min:
   ```
   python scripts/find_candidate_videos.py --check VIDEO_ID
   ```

2. Add to `data/video_list.xlsx`:
   - Add row with: url, domain, title, speaker, language, duration_est_min, num_chapters_est, source_channel

3. Download video:
   ```
   python scripts/download_all.py
   ```

4. Transcribe on vast.ai GPU (see CLAUDE.md for instance setup):
   ```
   python scripts/vast_transcribe.py
   python scripts/download_transcripts.py
   ```
   **Remember to destroy the instance immediately after!**

5. Process new videos:
   ```
   python src/lecseg/preprocess/sentence_split.py
   python src/lecseg/features/text_embeddings.py --model bge_large
   python src/lecseg/features/text_embeddings.py --model e5_large_v2
   # CLIP embeddings:
   python scripts/compute_clip_embeddings.py --video-id VIDEO_ID
   ```

6. Get YouTube GT:
   ```
   python scripts/fetch_youtube_chapters.py --video-id VIDEO_ID
   ```

7. Auto-annotate subtopics:
   ```
   python scripts/autoannotate.py --video-id VIDEO_ID
   ```

8. Review annotations (REQUIRED — human review):
   ```
   streamlit run scripts/annotate.py
   ```

9. Rerun eval on expanded dataset:
   ```
   python scripts/run_eval.py
   python scripts/tables.py
   python scripts/figures.py
   ```

## Estimated effort
- Per-video: 20-30 min GPU transcription + 30-60 min human annotation review
- 10 new videos: ~5-8 hours total
- Cost: ~$0.50-1.00 vast.ai GPU time
