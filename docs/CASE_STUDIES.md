# Qualitative Case Studies

Generated from `selector_choice_audit.json`, `domain_performance_analysis.json`, and `method_portfolio_analysis.json`.

These cases are intended for thesis discussion and defense slides. They turn the metric table into concrete interpretation: where the selector helps, where it fails, and why the oracle gap matters.

## Case 1 - Success: multimodal/cross-model evidence helps

- Video: `Hy7ou5R_vjE` - Vectors in Multiple Dimensions
- Domain: PHYSICS; chapters: 6
- Selector method: `mm_w11_frac65_over4_ocr0_pros10_shot10_min12_nms5` (multimodal-grid)

| Method | Pk | WD | BS | F1@2 |
|---|---:|---:|---:|---:|
| BGE-divisive baseline | 0.3125 | 0.3167 | 0.2250 | 0.2222 |
| Cross-model conservative | 0.2917 | 0.2917 | 0.0000 | 0.0000 |
| Balanced selector | 0.1375 | 0.2097 | 0.0000 | 0.0000 |

Interpretation: The selector substantially reduces Pk/WD relative to the cross-model method, showing that the method portfolio contains useful complementary evidence on some lectures.

## Case 2 - Failure: selector over-switching hurts

- Video: `j0wJBEZdwLs` - But what is a Laplace Transform?
- Domain: MATH; chapters: 8
- Selector method: `mm_w11_frac75_over4_ocr0_pros10_shot10_min12_nms1` (multimodal-grid)

| Method | Pk | WD | BS | F1@2 |
|---|---:|---:|---:|---:|
| BGE-divisive baseline | 0.3971 | 0.4081 | 0.0000 | 0.0000 |
| Cross-model conservative | 0.3805 | 0.4062 | 0.0000 | 0.0000 |
| Balanced selector | 0.4559 | 0.5239 | 0.0000 | 0.0000 |

Interpretation: The selector chooses an aggressive alternative that worsens Pk/WD. This is the core reason the thesis avoids claiming domain-general deployment.

## Case 3 - Domain weakness: Mathematics

Mathematics is the clearest domain-level failure case.

| Method | Pk | WD | F1@2 |
|---|---:|---:|---:|
| BGE-divisive baseline | 0.3724 | 0.3850 | 0.0984 |
| Cross-model conservative | 0.3792 | 0.3873 | 0.0217 |
| Balanced selector | 0.4014 | 0.4367 | 0.1208 |

Interpretation: math lectures often preserve vocabulary across real topic changes and contain ASR-sensitive notation. The selector gains exact-boundary hits but hurts Pk/WD, so Math needs domain-specific transcript and notation handling.

## Case 4 - Oracle gap: the next research problem

| Method | Pk | WD | F1@2 |
|---|---:|---:|---:|
| Best global cross-model | 0.3713 | 0.3764 | 0.0237 |
| Per-video method oracle | 0.2980 | 0.3280 | 0.1676 |

Interpretation: the method pool often contains better choices than the deployable selector can identify. The strongest next contribution is therefore boundary/method selection, not another raw candidate generator.
