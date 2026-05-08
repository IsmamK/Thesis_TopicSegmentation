import os
import json
import time
from tqdm import tqdm
import whisper
import torch

# === Configuration ===
VIDEO_DIR = "3_Implementation/Data/LectureVideos"
OUTPUT_DIR = "3_Implementation/Data/Transcripts"
MODEL_SIZE = "small"  # tiny, base, small, medium, large (smaller = faster on CPU)
DEBUG_SEGMENTS = False  # Set True to print first 50 chars of each segment

# === Device check ===
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Using device: {DEVICE}\n")

# === Load Whisper Model ===
print(f"[INFO] Loading Whisper model '{MODEL_SIZE}' on {DEVICE}...")
start_load = time.time()
model = whisper.load_model(MODEL_SIZE, device=DEVICE)
print(f"[INFO] Model loaded in {time.time() - start_load:.2f}s\n")

# === Ensure output directory exists ===
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Find all .mp4 files ===
video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")]
print(f"[INFO] Found {len(video_files)} videos in '{VIDEO_DIR}'\n")

# === Transcribe each video ===
total_start = time.time()
for idx, video_file in enumerate(video_files, 1):
    video_path = os.path.join(VIDEO_DIR, video_file)
    output_filename = os.path.splitext(video_file)[0] + "_whisper.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    print(f"[{idx}/{len(video_files)}] Processing: {video_file}")

    if os.path.exists(output_path):
        print(f"  [✓] Already transcribed, skipping.\n")
        continue

    try:
        video_start = time.time()
        print("  [→] Transcribing... This may take a while on CPU.")

        # Transcribe video
        result = model.transcribe(video_path, verbose=False)

        # Extract segments
        segments_data = []
        if "segments" in result:
            for seg in tqdm(result["segments"], desc="    Segments", unit="seg"):
                segments_data.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })
                if DEBUG_SEGMENTS:
                    print(f"      {seg['start']:.2f}-{seg['end']:.2f}: {seg['text'][:50]}...")

        transcript_data = {
            "segments": segments_data,
            "language": result.get("language", ""),
            "text": result.get("text", "")
        }

        # Save transcript
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)

        print(f"  [✓] Saved transcript in {time.time() - video_start:.2f}s\n")

    except Exception as e:
        print(f"  [ERROR] Failed to transcribe {video_file}: {e}\n")

print(f"✅ All transcriptions complete in {time.time() - total_start:.2f}s")
