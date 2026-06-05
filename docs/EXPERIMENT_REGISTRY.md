# Experiment Registry

Generated: 2026-06-05T08:38:28

This registry summarizes official and diagnostic experiments. A positive delta means worse than the official result.

| Rank | Status | Family | Method | Pk | WD | F1@2 | dPk | dWD | Artifact |
|---:|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | official_best | official | `method_selector_extra_trainrank_balanced_k80` | 0.3588 | 0.3739 | 0.0893 | +0.0000 | +0.0000 | `results/method_selector_significance.json` |
| 2 | diagnostic | selector | `extra` | 0.3634 | 0.3760 | 0.0608 | +0.0046 | +0.0021 | `results/method_selector_experiment_trainrank_balanced_k50.json` |
| 3 | diagnostic | selector | `extra` | 0.3663 | 0.3819 | 0.0837 | +0.0075 | +0.0080 | `results/method_selector_experiment_trainrank_balanced_k100.json` |
| 4 | diagnostic | selector | `extra` | 0.3678 | 0.3813 | 0.0642 | +0.0090 | +0.0074 | `results/method_selector_experiment_trainrank_balanced_k90.json` |
| 5 | diagnostic | selector | `extra` | 0.3693 | 0.3830 | 0.0693 | +0.0105 | +0.0091 | `results/method_selector_experiment_trainrank_balanced_k60.json` |
| 6 | diagnostic | selector | `extra` | 0.3695 | 0.3820 | 0.0772 | +0.0107 | +0.0081 | `results/method_selector_experiment_trainrank_balanced_k70.json` |
| 7 | rejected | cross_model_grid | `cross_e5_w8_frac60_minlen13` | 0.3734 | 0.3790 | 0.0197 | +0.0146 | +0.0051 | `results/eval_cross_model_tuning_focused_bge_e5.json` |
| 8 | rejected | cross_model_grid | `cross_e5large_w8_frac64_minlen11` | 0.3738 | 0.3786 | 0.0245 | +0.0150 | +0.0047 | `results/eval_cross_model_tuning_focused_bge_e5large.json` |
| 9 | rejected | cross_model_grid | `cross_bge_large_w8_frac64_minlen11` | 0.3781 | 0.3858 | 0.0366 | +0.0193 | +0.0119 | `results/eval_cross_model_tuning_focused_e5large_bge.json` |
| 10 | same_dataset_baseline | treeseg_same_dataset | `treeseg_local_mpnet_min6_lam0` | 0.4320 | 0.4673 | 0.1733 | +0.0732 | +0.0934 | `results/eval_treeseg_same_dataset_mpnet.json` |
| 11 | same_dataset_baseline | treeseg_same_dataset | `treeseg_local_e5large_min6_lam0` | 0.4322 | 0.4654 | 0.1576 | +0.0734 | +0.0915 | `results/eval_treeseg_same_dataset_e5large.json` |
| 12 | same_dataset_baseline | treeseg_same_dataset | `treeseg_local_bge_large_min6_lam0` | 0.4399 | 0.4780 | 0.1643 | +0.0811 | +0.1041 | `results/eval_treeseg_same_dataset_bge_large.json` |
