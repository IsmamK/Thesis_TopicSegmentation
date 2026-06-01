# Related-Work Comparison for LECSEG Positioning

This table is for thesis/paper positioning, not for claiming external state of
the art. The compared works use different datasets, annotation policies, units
of evaluation, and metrics. The defensible LECSEG claim is therefore local:
on LECSEG-30, the current best official run improves over the implemented
stable BGE-divisive baseline, while external systems are cited as context.

## LECSEG Reference Numbers

| System/result | Dataset | Metrics |
|---|---|---|
| LECSEG current best official run (`cross_e5_frac70_minlen11`) | LECSEG-30: 30 public YouTube lectures, 32.52 h, 419 chapters, 904 subtopics | Pk=0.3715, WD=0.3766, BS=0.0314, F1@2=0.0228 |
| LECSEG alignment-adjusted variant (`cross_e5_frac70_minlen11__align_contains_before`) | LECSEG-30 | Pk=0.3713, WD=0.3764, BS=0.0362, F1@2=0.0237 |
| Stable implemented baseline (BGE-divisive) | LECSEG-30 YouTube-GT clean copies in `results/eval_bert_wiki.json` / `results/eval_smoothing.json` | Pk=0.3884, WD=0.3956, BS=0.1292, F1@2=0.0878 |
| Candidate oracle diagnostic | LECSEG-30, oracle candidate selection using GT | tolerance 5: Pk=0.0066, WD=0.0082 |

## Directly Related Systems

| Work | Link | Data scale / domain | Supervision | Modalities | Metrics reported | Reported results most relevant to LECSEG | LECSEG stronger where | LECSEG weaker where | Positioning note |
|---|---|---:|---|---|---|---|---|---|---|
| MiniSeg / YTSEG (Retkowski & Waibel, EACL 2024) | https://arxiv.org/abs/2402.17633 | 19,299 English YouTube videos, 393 channels, 6,533 h; mixed spoken content including lectures, podcasts, news, creators | Supervised segmentation model trained on YTSEG; also online variants | Transcript text; dataset can support audio/video but reported MiniSeg segmentation is text-based | Boundary precision/recall/F1, Pk, Boundary Similarity; title generation metrics separately | YTSEG MiniSeg: P=45.44, R=41.48, F1=43.37, Pk=28.73, BS=35.74. WIKI-727K -> YTSEG: P=48.30, R=43.56, F1=45.81, Pk=27.13, BS=37.89. | Narrower educational-lecture focus; hierarchical chapter+subtopic annotation; local multimodal feature pipeline; no need to train a supervised neural segmenter for the official unsupervised result. | Much smaller benchmark; higher Pk than MiniSeg's YTSEG Pk if interpreted on the same 0-1 scale (0.3715 vs 0.2873); weaker boundary F1; no large supervised training. | Stronger external method. Do not claim LECSEG beats MiniSeg. Use MiniSeg/YTSEG as the closest transcript-chaptering benchmark and say LECSEG trades scale/model strength for lecture-specific hierarchy and reproducibility. |
| Chapter-Gen / Multi-modal Video Chapter Generation (Cao et al., 2022) | https://arxiv.org/abs/2209.12694 | 9,631 user-generated videos split 6,742/963/1,926; chapter timestamps and titles; easy/hard labels from 12 annotators | Supervised two-stage framework: chapter localization classifier plus title generator | Video frames + narration text; ResNet/TSM visual features, BERT text, Transformer/Pegasus/BigBird title generation | Localization AP, Recall@3s, Recall@5s; title ROUGE-1/2/L | Best localization visual+text: AP=43.3, Recall=25.8, Recall@3s=60.1, Recall@5s=76.1. Best title generation visual+text cross attention: ROUGE-1=34.4/25.6, ROUGE-2=13.4/8.8, ROUGE-L=34.0/25.3 for GT/predicted locations. | Open lecture segmentation pipeline with Pk/WD/BS/F1 evaluation; hierarchical labels; explicit oracle/error analysis; lecture-specific reproducibility rather than generic user-generated videos. | Chapter-Gen is larger, supervised, and substantially stronger on near-boundary localization metrics; LECSEG F1@2 is very low by comparison. | Stronger external method for supervised video chapter generation. LECSEG should cite it as evidence that multimodal supervised learning works, while LECSEG's unsupervised local pipeline is a different thesis scope. |
| VidChapters-7M (Yang et al., NeurIPS 2023 Datasets & Benchmarks) | https://antoyang.github.io/vidchapters.html and https://arxiv.org/abs/2309.13952 | 817K user-chaptered videos, 7M chapters; average 23 min/video; 12 YouTube categories with at least 20K videos each | Large-scale supervised/finetuned video-language benchmark; also zero-shot baselines | Speech transcripts + visual features; Vid2Seq and PDVC baselines | SODA_c, BLEU, CIDEr, METEOR, ROUGE-L for generation; localization R/P at seconds and IoU thresholds | Best full generation in paper: Vid2Seq speech+visual with C4+HowTo100M finetuning SODA_c=11.4. Localization: R@5s=36.4, R@3s=28.5, R@0.5=48.2, R@0.7=28.5, P@5s=30.3, P@3s=24.0, P@0.5=43.1, P@0.7=26.4. | Much more focused educational lecture corpus; hierarchical subtopic layer; easier to audit and reproduce locally; Pk/WD evaluation suitable for topic-segmentation thesis. | Orders of magnitude smaller; no large-scale pretraining; weaker external benchmark significance; no comparable generation SODA/CIDEr result. | Dataset/benchmark is far stronger at scale. Use it to position LECSEG as a small, lecture-specific, hierarchical benchmark, not as a replacement. |
| Chapter-Llama (Ventura et al., CVPR 2025) | https://arxiv.org/abs/2504.00072 | Hour-long videos evaluated on VidChapters-7M | Trained LLM chapterer | Speech transcripts + selected frame captions with timestamps | Chaptering F1 and title/timestamp quality on VidChapters-7M | Abstract reports 45.3 F1 vs 26.7 previous SOTA on VidChapters-7M. | Smaller local reproducible benchmark; simpler non-LLM core; explicit candidate-oracle bottleneck analysis. | Much stronger external result; uses large-context LLM training and VidChapters-scale supervision. | Cite as newer evidence that trained LLM chaptering is strong. LECSEG should not compete with this claim; it motivates future work on candidate selection and learned reranking. |
| TreeSeg (Gklezakos et al., 2024) | https://arxiv.org/abs/2407.12028 | TinyRec: 21 self-recorded lectures; also ICSI/AMI meeting corpora | Unsupervised / no learnable parameters | Text transcript embeddings | Pk | Reported Pk=0.367 on TinyRec, Pk=0.310 on ICSI, Pk=0.355 on AMI. | Multimodal and hierarchical lecture artifact; public YouTube lecture seed benchmark; broader pipeline and evaluation utilities. | LECSEG current best Pk=0.3715 is slightly worse than TreeSeg TinyRec Pk=0.367, and datasets are not shared. | Very close unsupervised text-only competitor. Do not claim a win. A fair claim requires running TreeSeg on LECSEG-30 or LECSEG on TinyRec. |
| AVLectures (Singh S et al., 2022) | https://arxiv.org/abs/2210.16644 | 86 STEM courses, 2,350+ lectures | Self-supervised representation learning / clustering | Audio-visual, OCR/text, video | Task-specific clustering/lecture-understanding metrics, not directly Pk/WD comparable | Reports improvements over visual+textual baselines for AV lecture understanding. | Pk/WD/BS/F1 thesis evaluation; explicit chapter/subtopic output; local end-to-end pipeline. | AVLectures is much larger and more naturally multimodal for lecture video representation. | Related as a multimodal lecture-video resource, not a direct boundary-metric competitor. |

## Thesis-Safe Comparison Language

Use language like:

> Recent large-scale and supervised chaptering systems such as MiniSeg/YTSEG,
> Chapter-Gen, VidChapters-7M, and Chapter-Llama report stronger external
> performance or much larger training/evaluation corpora. LECSEG does not claim
> external state-of-the-art performance. Its contribution is a reproducible
> educational-lecture segmentation benchmark and pipeline, with statistically
> supported local Pk/WindowDiff improvement over implemented baselines,
> multimodal/error analysis, hierarchical annotations, and oracle evidence that
> candidate selection is the primary bottleneck.

Avoid language like:

- "LECSEG outperforms state-of-the-art video chaptering systems."
- "LECSEG is better than MiniSeg/YTSEG."
- "LECSEG is competitive with VidChapters-7M" unless explicitly limited to
  reproducibility/lecture hierarchy, not raw performance or scale.

## Source Notes

- MiniSeg/YTSEG: the paper states YTSEG has 19,299 English YouTube videos and
  reports MiniSeg YTSEG Pk=28.73 and BS=35.74.
- Chapter-Gen: the paper reports 6,742/963/1,926 train/validation/test videos,
  localization AP=43.3 and Recall@5s=76.1 for visual+text, and title ROUGE-L
  34.0/25.3 for GT/predicted locations using cross-attention fusion.
- VidChapters-7M: the paper and project page state 817K videos and 7M chapters;
  the reported best Vid2Seq speech+visual full generation result is SODA_c=11.4.
- Chapter-Llama: the abstract reports 45.3 vs 26.7 F1 on VidChapters-7M.
- TreeSeg and AVLectures are included because they are close lecture/video
  segmentation references already used in the project literature matrix.
