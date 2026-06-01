# Thesis Result Tables

Generated from current result JSON files. Do not edit numbers manually; rerun
`python scripts/generate_thesis_result_tables.py` after changing results.

## Main Results

| Method | Pk | WD | BS | F1@2 | Role |
| --- | --- | --- | --- | --- | --- |
| BGE-divisive baseline | 0.3884 | 0.3956 | 0.1292 | 0.0878 | Strong implemented baseline |
| Cross-model conservative | 0.3713 | 0.3764 | 0.0362 | 0.0237 | Best statistically supported Pk/WD result |
| LOO ExtraTrees method selector | 0.3588 | 0.3739 | 0.0757 | 0.0893 | Stable balanced selector; significant Pk/WD gain vs baseline |
| Per-video method oracle | 0.2980 | 0.3280 | 0.1366 | 0.1676 | Diagnostic upper bound, not deployable |

## Significance

| Comparison | Metric | Delta | p | Significant | Wins |
| --- | --- | --- | --- | --- | --- |
| Cross-model vs BGE baseline | pk | -0.0171 | 0.0064 | yes | 22/30 |
| Cross-model vs BGE baseline | wd | -0.0193 | 0.0001 | yes | 26/30 |
| Cross-model vs BGE baseline | boundary_similarity | -0.0930 | 0.0074 | yes | 4/30 |
| Cross-model vs BGE baseline | f1_tol2 | -0.0641 | 0.0090 | yes | 4/30 |
| Selector vs cross-model | pk | -0.0126 | 0.3560 | no | 9/30 |
| Selector vs cross-model | wd | -0.0025 | 0.9039 | no | 7/30 |
| Selector vs cross-model | boundary_similarity | 0.0395 | 0.0076 | yes | 10/30 |
| Selector vs cross-model | f1_tol2 | 0.0656 | 0.0076 | yes | 10/30 |
| Selector vs BGE baseline | pk | -0.0296 | 0.0252 | yes | 19/30 |
| Selector vs BGE baseline | wd | -0.0217 | 0.0238 | yes | 23/30 |
| Selector vs BGE baseline | boundary_similarity | -0.0534 | 0.1541 | no | 8/30 |
| Selector vs BGE baseline | f1_tol2 | 0.0015 | 0.9170 | no | 9/30 |

## External Scale

| Work | Videos | Scale | Metrics | Positioning |
| --- | --- | --- | --- | --- |
| LECSEG-30 | 30 | 32.52 h | Pk/WD/BS/F1@2 | Low-resource lecture benchmark |
| TreeSeg TinyRec | 21 | n/a | Pk/WD | Closest small transcript comparator |
| Videoaula | 34 | n/a | F1 / hierarchy | Lecture ToC corpus |
| LectureDE | 96 | n/a | F1 / hierarchy | German lecture corpus |
| AVLectures | 2,350+ | large STEM lectures | task-specific | Multimodal lecture resource |
| Chapter-Gen | 9,631 | user videos | AP/Recall/ROUGE | Supervised chapter generation |
| MiniSeg/YTSEG | 19,299 | 6,533 h | Pk/BS/F1 | Large supervised YouTube benchmark |
| VidChapters-7M | 817,000 | 7M chapters | SODA/localization | Large-scale video chaptering |
