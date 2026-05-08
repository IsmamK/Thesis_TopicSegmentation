from pathlib import Path
import re

summary_dir = Path("papers_summary")
out_path = Path("docs/LITERATURE_MATRIX.md")
out_path.parent.mkdir(exist_ok=True)

expected = [
    ("hearst1997.md", "Hearst / TextTiling", "1997", "Text", "Lexical cohesion / vocabulary shift", "Text passages / expository text", "Pk-style segmentation error; qualitative boundary agreement", "Text-only; no audio, visual, slide, or lecture-specific signals", "N1, N2"),
    ("beeferman1999.md", "Beeferman et al. / Pk", "1999", "Text / metric", "Statistical segmentation model and Pk evaluation", "Text segmentation corpora", "Pk metric", "Metric penalizes boundary errors within a fixed window but does not fully capture near-boundary similarity", "N6"),
    ("choi2000.md", "Choi / C99", "2000", "Text", "Rank matrix and divisive clustering", "Synthetic and text segmentation datasets", "Pk / segmentation accuracy", "Domain-independent text segmentation only; no multimodal lecture cues", "N1, N2"),
    ("pevzner2002.md", "Pevzner & Hearst / WindowDiff", "2002", "Text / metric", "WindowDiff evaluation metric", "Text segmentation benchmark examples", "WindowDiff", "Evaluation-focused paper; does not provide multimodal segmentation method", "N6"),
    ("fournier2013.md", "Fournier / Boundary Similarity", "2013", "Text / metric", "Boundary edit distance / boundary similarity", "Text segmentation evaluation cases", "Boundary similarity score", "Metric improves evaluation but does not address lecture-video segmentation features", "N6"),
    ("tuna2015.md", "Tuna et al. / Classroom Videos", "2015", "Lecture video", "Classroom lecture video segmentation using visual/audio/slide cues", "Classroom videos", "Lecture segmentation metrics reported in paper", "Focused on classroom-video setting; limited general benchmark diversity", "N1, N5"),
    ("zhang2016.md", "Zhang et al. / MOOC Segmentation", "2016", "MOOC video", "MOOC lecture segmentation", "MOOC videos", "Segmentation quality metrics reported in paper", "MOOC-specific assumptions; may not generalize across lecture styles and subjects", "N5, N6"),
    ("che2018.md", "Che & Yang / Slide Synchronization", "2018", "Slides + video", "Slide/video synchronization and alignment", "Lecture slide-video material", "Alignment/synchronization quality", "Primarily slide synchronization rather than hierarchical topic segmentation", "N2, N3"),
    ("gandhi2018.md", "Gandhi et al. / Visually Salient Words", "2018", "Visual + text", "Visually salient word extraction for lecture understanding", "Lecture video / slide text", "Keyword or saliency quality metrics", "Uses salient visual words but does not integrate full transcript, prosody, and LLM refinement", "N1, N2, N4"),
    ("sener2018.md", "Sener & Yao / Activity Segmentation", "2018", "Video", "Unsupervised activity segmentation", "Activity videos", "MoF / F1 / segmentation metrics", "Targets physical activity videos, not spoken educational lecture topic boundaries", "N5, N6"),
    ("reimers2019.md", "Reimers & Gurevych / Sentence-BERT", "2019", "Text embeddings", "Siamese BERT sentence embeddings", "NLI / STS datasets", "STS benchmark correlation", "Provides embeddings, not a complete lecture segmentation pipeline", "N1"),
    ("sun2019.md", "Sun et al. / Contrastive Bidirectional Transformer", "2019", "Text", "Contrastive bidirectional transformer for segmentation", "Text segmentation datasets", "Pk / WindowDiff", "Text-only neural segmentation; no lecture audio/visual evidence", "N1, N2"),
    ("chand2021.md", "Chand & Ogul / Lecture Video Segmentation", "2021", "Lecture video", "Framework for lecture video segmentation", "Lecture videos", "Segmentation metrics reported in paper", "Framework-level study; limited emphasis on reproducible local-LLM refinement and new dataset seed", "N4, N5"),
    ("dss2023.md", "D.S.S. et al. / AVLectures", "2023", "Audio-visual lecture", "Audio-visual lecture understanding / segmentation resource", "AVLectures", "Task metrics reported in paper", "Dataset/resource focus; does not fully cover our local reproducible boundary-refinement pipeline", "N4, N5, N7"),
    ("fan2023.md", "Fan et al. / Topic Segmentation via LLMs", "2023", "Text + LLM", "LLM-based topic segmentation", "Text/topic segmentation datasets", "Pk / WindowDiff / LLM evaluation", "LLM use may rely on closed or large models; less focus on local reproducibility and lecture multimodality", "N4, N7"),
    ("freisinger2023.md", "Freisinger et al. / Multilingual Topic Segmentation", "2023", "Text / multilingual", "Unsupervised multilingual topic segmentation", "Multilingual text/speech transcripts", "Pk / WindowDiff", "Multilingual focus; not centered on multimodal lecture-video segmentation with slide and audio cues", "N1, N2, N5"),
    ("radford2023.md", "Radford et al. / Whisper", "2023", "Audio ASR", "Large-scale weakly supervised speech recognition", "680k hours weakly supervised audio", "WER across speech benchmarks", "ASR model only; does not solve topic boundary detection or lecture segmentation by itself", "N1"),
    ("karim2024.md", "Karim et al. / MED-VT++", "2024", "Multimodal video", "Multimodal transformer for medical video tasks", "Medical video datasets", "Task-specific classification/segmentation metrics", "Medical-video focus; not lecture topic segmentation with educational chapter boundaries", "N2, N5"),
    ("yu2024.md", "Yu et al. / Multimodal Fusion & Coherence Modeling", "2024", "Multimodal", "Fusion and coherence modeling", "Multimodal datasets", "Coherence / task metrics reported in paper", "General multimodal coherence approach; not packaged as lecture dataset and boundary-evaluation pipeline", "N2, N6, N7"),
    ("wei2024.md", "Wei et al. / PreMind", "2024", "Multimodal / prediction", "PreMind-style predictive multimodal modeling", "Multimodal datasets", "Prediction metrics reported in paper", "Predictive modeling focus; not specifically lecture topic segmentation or creator-chapter ground truth", "N5, N7"),
]

def clean_cell(x: str) -> str:
    return x.replace("|", "/").replace("\n", " ").strip()

rows = []
missing_files = []

for filename, paper, year, modality, method, dataset, metric, limitation, novelty in expected:
    path = summary_dir / filename
    if not path.exists():
        missing_files.append(filename)
    rows.append([
        f"[{paper}](../papers_summary/{filename})",
        year,
        modality,
        method,
        dataset,
        metric,
        limitation,
        novelty,
    ])

if missing_files:
    print("WARNING missing summary files:", missing_files)

# Sort by year
rows.sort(key=lambda r: int(re.sub(r"\D", "", r[1]) or 9999))

content = []
content.append("# Literature Review Matrix\n")
content.append("_Built from the 20 T06 paper summaries. This v2 matrix compares method, modality, dataset, metrics, limitations, and how each gap maps to LECSEG novelty claims._\n")
content.append("\n| Paper | Year | Modality | Method | Dataset | Best Metric | Limitation | Our-novelty-addresses |")
content.append("|---|---:|---|---|---|---|---|---|")

for r in rows:
    content.append("| " + " | ".join(clean_cell(c) for c in r) + " |")

content.append("\n## Gap Analysis\n")
content.append("- **Gap 1 — Text-only segmentation misses lecture-specific evidence (N1, N2):** Classical and neural text segmentation papers such as TextTiling, C99, SBERT-based approaches, and contrastive transformer segmentation mainly operate on text, while LECSEG combines transcript, visual/slide, and audio-prosody signals.")
content.append("- **Gap 2 — Evaluation metrics exist, but pipeline-level lecture validation is limited (N6):** Pk, WindowDiff, and Boundary Similarity help evaluate boundaries, but LECSEG connects these metrics to a reproducible lecture-video pipeline and thesis-ready result tables.")
content.append("- **Gap 3 — Prior lecture-video systems are narrow in dataset/source diversity (N5):** MOOC/classroom-focused systems often use a specific lecture setting; LECSEG-30 deliberately spans 5 subject domains and multiple presentation styles.")
content.append("- **Gap 4 — Slide or visual cue work is not enough for full topic segmentation (N2, N3):** Slide synchronization and visually salient word methods capture useful visual structure, but LECSEG turns multimodal evidence into explicit segment boundaries and chapter-like outputs.")
content.append("- **Gap 5 — LLM segmentation work may not be locally reproducible (N4, N7):** LLM-based topic segmentation can depend on closed or large models; LECSEG uses local Ollama models for boundary refinement and title generation to support reproducibility.")
content.append("- **Gap 6 — ASR models are components, not complete segmentation systems (N1):** Whisper provides robust transcripts, but LECSEG builds downstream sentence segmentation, embedding, boundary detection, and evaluation on top of ASR.")
content.append("- **Gap 7 — General multimodal/video papers do not target educational chapter ground truth (N5, N6):** Activity, medical, and general multimodal-video approaches do not directly optimize against creator-provided lecture chapters; LECSEG uses these chapter boundaries as dataset seed ground truth.")

out_path.write_text("\n".join(content) + "\n", encoding="utf-8")
print(f"Wrote {out_path} with {len(rows)} rows.")
