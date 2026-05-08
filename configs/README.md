# Hydra configs

`defaults.yaml` is the single source of truth for runtime parameters.

## Override on the command line

```
python -m lecseg segment data/transcripts/lec01.json \
    fusion.mode=fixed \
    refine.enable=false \
    seed=1337
```

## Per-experiment files (recommended)

For named ablations, copy `defaults.yaml` to `configs/exp/<name>.yaml` and
override only what changes. Then:

```
python -m lecseg segment data/transcripts/lec01.json --config-name exp/<name>
```

`results/<run>/config.yaml` will record the fully-resolved config so the run
can be reproduced exactly.

## Don't

- Don't edit `defaults.yaml` for one-off experiments — that breaks reproducibility.
- Don't mix Hydra and `argparse` in the same script.
