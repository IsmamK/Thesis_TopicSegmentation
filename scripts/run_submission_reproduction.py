"""One-command submission reproduction checklist.

This script runs the lightweight gates that should pass before submission. It
does not redownload data or recompute all embeddings by default; those are
long-running data-production steps. The purpose is to verify the published
repository state: tests, claim discipline, readiness audit, generated registry,
and thesis PDF build.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def _run(cmd: list[str], cwd: Path = ROOT) -> None:
    print(f"\n$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-pdf", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    if not args.skip_tests:
        _run([str(PY), "-m", "pytest", "tests", "-q"])
    _run([str(PY), "scripts/experiment_registry.py"])
    _run([str(PY), "scripts/validate_thesis_claims.py"])
    _run([str(PY), "scripts/submission_readiness_audit.py"])
    if not args.skip_pdf:
        _run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=ROOT / "thesis")
        _run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], cwd=ROOT / "thesis")
    print("\nReproduction gates completed.")


if __name__ == "__main__":
    main()
