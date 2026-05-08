# data/

Intermediate data artifacts produced by the preprocessing pipeline.

| Subfolder    | Contents |
|---|---|
| `raw/`       | Original lecture video files — **never committed to git** |
| `whisper/`   | Whisper transcription JSON files |
| `sentences/` | Sentence-split transcripts |
| `shots/`     | Shot-boundary frame indices |
| `ocr/`       | PaddleOCR slide text per frame |
| `prosody/`   | Pause, pitch, and energy feature CSVs |
| `emb_text/`  | Sentence-level text embedding arrays (.npy) |
| `emb_visual/`| CLIP visual embedding arrays (.npy) |
| `features/`  | Fused per-sentence feature matrix |
| `gt/`        | Ground-truth chapter timestamps (flat) |
| `gt_hier/`   | Ground-truth hierarchical annotations |
| `release/`   | Curated LECSEG-30 dataset release bundle |
| `llm_cache/` | Cached LLM responses (saves re-querying) |

## How to populate

Run `make reproduce` from the project root, or individual pipeline steps in `src/lecseg/preprocess/`.
