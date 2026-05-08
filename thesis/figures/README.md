# Figures directory

All thesis figures live here as **vector PDFs** (preferred) or 300+ DPI PNGs.

Naming convention: `<chapter>_<short>.pdf`. Examples:
- `pipeline.pdf` — overall \lecseg{} architecture (Chapter 3)
- `ch3_fusion.pdf` — reliability-weighted fusion module (Chapter 3)
- `ch4_main_bars.pdf` — main results bar chart (Chapter 4)
- `ch4_ablation_*.pdf` — one per ablation
- `ch4_error_strip.pdf` — gold-vs-prediction strip plots

Figures are produced by scripts in `src/lecseg/viz/` and saved here automatically.
Do not commit raster screenshots — re-export from the source script.

Use a colour-blind safe palette (`viridis`, `cividis`, or Okabe-Ito). Test in
greyscale before finalising.
