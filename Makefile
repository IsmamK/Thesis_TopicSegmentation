# LECSEG — Makefile
# One-line shortcuts for the most common project commands.
# Run `make help` to list all targets.

.PHONY: help install install-dev test lint format clean today next status \
        thesis paper webapp poster slides reproduce check pre-defense \
        strip-internal lit-matrix dashboard html

help:           ## Show this help message
	@echo ""
	@echo "LECSEG project — common commands"
	@echo "================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ----- Setup -----
install:        ## Install runtime dependencies (pip install -e .)
	pip install -e .

install-dev:    ## Install dev tools (ruff, black, pytest, pre-commit)
	pip install -e ".[dev]"
	pre-commit install

# ----- Daily flow -----
today:          ## Show the daily dashboard + the next task
	python scripts/today.py

next:           ## Print only the next task
	python scripts/next.py

status:         ## Regenerate STATUS.md and NEXT.md from progress.yaml
	python scripts/update_status.py

dashboard:      ## Plain terminal dashboard (no progress prompts)
	python scripts/dashboard.py

html:           ## Build & open the HTML progress dashboard
	python scripts/visualize_progress.py

# ----- Code quality -----
test:           ## Run the test suite
	pytest -q

lint:           ## Lint the codebase with ruff
	ruff check src tests scripts

format:         ## Auto-format code with black
	black src tests scripts

# ----- Research outputs -----
reproduce:      ## End-to-end reproduce every numerical claim of the thesis
	python -m lecseg.cli reproduce-all

lit-matrix:     ## Rebuild docs/LITERATURE_MATRIX.md from papers_summary/
	python scripts/build_literature_matrix.py

# ----- Deliverables -----
thesis:         ## Build the thesis PDF (thesis/main.pdf)
	cd thesis && pdflatex -interaction=nonstopmode main.tex && \
	  bibtex main && pdflatex -interaction=nonstopmode main.tex && \
	  pdflatex -interaction=nonstopmode main.tex

paper:          ## Build the IEEE paper PDF (paper/ieee.pdf)
	cd paper && pdflatex -interaction=nonstopmode ieee.tex && \
	  bibtex ieee && pdflatex -interaction=nonstopmode ieee.tex && \
	  pdflatex -interaction=nonstopmode ieee.tex

webapp:         ## Run the Streamlit demo (http://localhost:8501)
	streamlit run webapp/app.py

poster:         ## Build the A1 defense poster (poster/poster.pdf)
	cd poster && pdflatex -interaction=nonstopmode poster.tex

slides:         ## Build the defense slide deck (slides/slides.pdf)
	cd slides && pdflatex -interaction=nonstopmode slides.tex && \
	  pdflatex -interaction=nonstopmode slides.tex

# ----- Pre-submission -----
check:          ## Run the full pre-defense checklist
	python scripts/pre_defense_check.py

pre-defense: check  ## Alias for `check`

strip-internal: ## Dry-run the internal-files stripper (will not modify)
	python scripts/strip_internal.py --dry-run

# ----- Cleanup -----
clean:          ## Remove caches, build artifacts, & LaTeX intermediates
	rm -rf .pytest_cache .ruff_cache __pycache__ */__pycache__ */*/__pycache__
	rm -rf build dist *.egg-info
	cd thesis 2>/dev/null && rm -f *.aux *.log *.bbl *.blg *.toc *.out *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz || true
	cd paper  2>/dev/null && rm -f *.aux *.log *.bbl *.blg *.toc *.out *.lof *.lot *.fls *.fdb_latexmk *.synctex.gz || true
