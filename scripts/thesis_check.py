"""Automated thesis review checks for T37.

The checker is intentionally conservative: it does not prove academic quality,
but it catches submission-blocking issues such as missing figures, unresolved
references, placeholders, and untracked result-table evidence.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THESIS = ROOT / "thesis"

PLACEHOLDERS = re.compile(r"TODO|FIXME|XXX|\?\.\??|\bTBD\b", re.IGNORECASE)
BAD_LOG = re.compile(r"undefined references|undefined citation|Citation .* undefined|Reference .* undefined|There were undefined", re.IGNORECASE)
OVERFULL = re.compile(r"Overfull \\hbox .*?([0-9.]+)pt too wide")


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=120)
        return proc.returncode, proc.stdout + proc.stderr
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"Command timed out: {' '.join(cmd)}"


def compile_thesis() -> list[str]:
    issues: list[str] = []
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        ["bibtex", "main"],
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
        ["pdflatex", "-interaction=nonstopmode", "main.tex"],
    ]
    for cmd in commands:
        code, output = _run(cmd, THESIS)
        if code != 0:
            issues.append(f"Compile command failed ({code}): {' '.join(cmd)}")
            issues.append(output[-2000:])
            break
    return issues


def check_log() -> list[str]:
    issues: list[str] = []
    log_path = THESIS / "main.log"
    if not log_path.exists():
        return ["Missing thesis/main.log"]
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    if BAD_LOG.search(text):
        issues.append("Unresolved citation/reference warning found in main.log")
    overfull_values = [float(m.group(1)) for m in OVERFULL.finditer(text)]
    severe = [v for v in overfull_values if v > 10.0]
    if severe:
        issues.append(f"Severe overfull hbox warnings >10pt: {severe[:10]}")
    return issues


def check_placeholders() -> list[str]:
    issues: list[str] = []
    for path in list((THESIS / "chapters").glob("*.tex")) + list((THESIS / "frontmatter").glob("*.tex")) + list((THESIS / "appendices").glob("*.tex")):
        for idx, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if PLACEHOLDERS.search(line):
                issues.append(f"Placeholder in {path.relative_to(ROOT)}:{idx}: {line.strip()}")
    return issues


def check_figures() -> list[str]:
    issues: list[str] = []
    figure_refs: set[str] = set()
    pattern = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
    for path in THESIS.rglob("*.tex"):
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lstrip().startswith("%"):
                continue
            for match in pattern.finditer(line):
                figure_refs.add(match.group(1))
    for ref in sorted(figure_refs):
        candidates = []
        raw = THESIS / ref
        candidates.append(raw)
        if raw.suffix == "":
            candidates.extend([raw.with_suffix(ext) for ext in [".pdf", ".png", ".jpg"]])
        if not any(p.exists() and p.stat().st_size > 1000 for p in candidates):
            issues.append(f"Missing or tiny figure referenced by thesis: {ref}")
    return issues


def check_tables_have_sources() -> list[str]:
    issues: list[str] = []
    expected = {
        "main_results.tex": "results/method_selector_significance.json",
        "significance.tex": "results/method_selector_significance.json",
        "domain_performance.tex": "results/domain_performance_analysis.json",
        "selector_leave_domain_out.tex": "results/selector_leave_domain_out.json",
        "modern_metrics.tex": "results/modern_metrics_summary.json",
        "claim_evidence_caveat.tex": "docs/DEFENSIBLE_CLAIMS.md",
        "llm_fusion_status.tex": "results/eval_llm_zero_shot_llama3_1_8b.json",
    }
    for table, source in expected.items():
        if not (THESIS / "tables" / table).exists():
            issues.append(f"Missing thesis table: {table}")
        if not (ROOT / source).exists():
            issues.append(f"Missing evidence source for {table}: {source}")
    return issues


def main() -> int:
    issues: list[str] = []
    issues.extend(compile_thesis())
    issues.extend(check_log())
    issues.extend(check_placeholders())
    issues.extend(check_figures())
    issues.extend(check_tables_have_sources())

    pdf = THESIS / "main.pdf"
    if not pdf.exists() or pdf.stat().st_size < 100_000:
        issues.append("Missing or tiny thesis/main.pdf")

    if issues:
        print("THESIS CHECK: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("THESIS CHECK: PASS")
    print(f"PDF: {pdf} ({pdf.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
