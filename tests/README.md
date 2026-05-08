# Tests

```
pytest -q                 # run everything fast
pytest -q -m "not slow"   # skip the slow / GPU tests
pytest tests/test_metrics.py
```

## Layout

- `test_smoke.py` — lightweight imports + CLI sanity. Must always pass.
- `test_metrics.py` — unit tests for the 5 evaluation metrics (filled in T22).
- `test_fusion.py`, `test_boundary.py`, etc. are added by the corresponding
  task that implements the module.

## Markers

- `@pytest.mark.slow` — runtime > 5 seconds.
- `@pytest.mark.gpu` — requires CUDA / MPS.

Skip both in CI by default; run nightly.
