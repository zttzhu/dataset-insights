# AGENTS.md

Guidance for coding agents working in `dataset-insights`.

## 1) Scope and Goals
- This repo is a Python CLI for quick CSV dataset orientation.
- Prefer minimal, targeted changes over broad refactors.
- Preserve existing CLI behavior and output contracts unless asked.
- Follow established patterns under `src/dataset_insights/`.

## 2) Repository Map
- `pyproject.toml`: package metadata, dependencies, CLI entrypoint.
- `README.md`: user docs and command examples.
- `src/dataset_insights/cli.py`: Click CLI command flow.
- `src/dataset_insights/analyze.py`: CSV load + core statistics.
- `src/dataset_insights/reports.py`: markdown/csv/json writers.
- `src/dataset_insights/plots.py`: PNG plot generation.
- `tests/conftest.py`: shared test fixtures.
- `tests/test_analyze.py`: analysis-layer unit tests.
- `tests/test_cli.py`: CLI integration tests.

## 3) Environment Setup
- Python version: `>=3.10`.
- Editable install: `python -m pip install -e .`
- Dev install: `python -m pip install -e .[dev]`
- README alternative: `uv pip install .`

## 4) Build, Lint, and Test Commands

### Run Commands
- Top-level help: `dataset-insights --help`
- Analyze help: `dataset-insights analyze --help`
- Analyze sample file: `dataset-insights analyze data/sample.csv --outdir reports/`

### Test Commands
- Run all tests: `pytest tests/`
- Quiet run: `pytest tests/ -q`
- Stop on first failure: `pytest tests/ -x`
- Single test file: `pytest tests/test_analyze.py`
- Single important test: `pytest tests/test_analyze.py::test_compute_missingness_values`
- Single CLI test: `pytest tests/test_cli.py::test_analyze_output_files`
- Filter by keyword: `pytest tests/ -k missingness`
- Alternate invocation: `python -m pytest tests/test_analyze.py::test_load_csv_latin1`

### Build Commands
- No dedicated build script is configured.
- Optional package build (if installed): `python -m build`

### Lint / Format Status
- No linter/formatter is configured in `pyproject.toml`.
- Do not assume Ruff, Black, or Flake8 are required.
- Main quality gate in this repo is tests + readable style.

## 5) Code Style and Conventions

### Imports
- Keep `from __future__ import annotations` in Python modules.
- Import order: standard library, third-party, local package.
- Use explicit imports; avoid wildcard imports.

### Formatting
- Follow PEP 8 and keep functions readable.
- Keep string style consistent with project (double quotes).
- Add comments only for non-obvious logic.
- Keep docstrings concise and practical.

### Types
- Add type hints on parameters and return types.
- Prefer modern type syntax (`str | Path`, `list[dict]`).
- Keep public helper return types explicit.

### Naming
- `snake_case` for functions and variables.
- `UPPER_SNAKE_CASE` for constants.
- Tests should read like behavior, e.g. `test_<behavior>`.
- Use descriptive names; short names like `df`/`ax` are acceptable locally.

### Data and Pandas
- Prefer vectorized pandas ops (`isna`, `sum`, `describe`, `corr`).
- Use `pathlib.Path` for path operations.
- Keep transformations explicit and local.
- Avoid global mutable state.
- Preserve output schema unless a task explicitly changes it.

### CLI Conventions
- Use Click (`click.echo`) for user-facing text.
- Keep console output concise and informative.
- Preserve existing skip message style (`Skipped: ...`).
- Keep non-zero exits for invalid input/data problems.

### Error Handling
- For expected user/data issues, provide clear messages.
- Existing load-failure pattern in `analyze.py` is:
  - print to stderr
  - `sys.exit(1)`
- Avoid noisy tracebacks for expected bad input.
- Catch specific exceptions where practical.

## 6) Testing Guidance
- Add reusable fixtures in `tests/conftest.py`.
- Put analysis logic tests in `tests/test_analyze.py`.
- Put CLI and output-behavior tests in `tests/test_cli.py`.
- For behavior changes, update or add the nearest tests.
- Use `tmp_path` for filesystem isolation.
- Keep tests deterministic and focused.

Suggested verification order:
1. Run the most targeted single test.
2. Run the affected test file.
3. Run the full suite: `pytest tests/`.

## 7) Output File Contract
- Keep output names stable unless explicitly requested otherwise:
  - `summary.md`
  - `summary_statistics.csv`
  - `schema.json`
  - `missingness.csv`
  - `correlation.csv`
  - `plots/distribution_histogram.png`
  - `plots/correlation_heatmap.png`
  - `plots/missingness_bar.png`
- Writer/plot functions should return output `Path` values.
- Ensure output directories exist using `mkdir(parents=True, exist_ok=True)`.

## 8) Documentation Rules
- Update `README.md` when behavior changes are user-visible.
- Keep docs aligned with actual command behavior and outputs.
- Do not document features that are not implemented.

## 9) Dependency and Change Hygiene
- Keep diffs tightly scoped to the task.
- Avoid unrelated formatting churn.
- Do not add dependencies unless necessary.
- If adding dependencies, update `pyproject.toml` and explain why.

## 10) Git Hygiene for Agents
- Avoid touching unrelated files.
- Do not rewrite history unless explicitly requested.
- Keep commits coherent and reviewable.
- Prefer feature branches for PRs; avoid direct pushes to `main`.

## 11) Cursor / Copilot Rule Files
Checked for additional instruction files:
- `.cursor/rules/`: not present
- `.cursorrules`: not present
- `.github/copilot-instructions.md`: not present

No additional Cursor/Copilot instruction files are currently active in this repo.

## 12) Quick Agent Checklist
- Read relevant source and tests before editing.
- Implement the smallest acceptable change.
- Add or update tests for behavior changes.
- Run targeted tests, then broader suite.
- Update docs for user-visible changes.
- Keep patches simple and maintainable.
