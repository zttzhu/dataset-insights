# AGENTS.md

Guidance for coding agents working in `dataset-insights`.

## 1) Scope
- This is a Python CLI for quick CSV dataset orientation.
- Prefer minimal, targeted changes over broad refactors.
- Preserve existing CLI behavior and output file contracts unless asked.
- Follow existing patterns in `src/dataset_insights/`.

## 2) Repo Layout
- `pyproject.toml`: metadata, dependencies, script entrypoint.
- `README.md`: user docs and command examples.
- `src/dataset_insights/cli.py`: Click CLI flow.
- `src/dataset_insights/analyze.py`: load CSV + compute stats.
- `src/dataset_insights/reports.py`: writes markdown/csv/json outputs.
- `src/dataset_insights/plots.py`: writes PNG plots.
- `tests/conftest.py`: fixtures.
- `tests/test_analyze.py`: unit tests.
- `tests/test_cli.py`: CLI integration tests.

## 3) Environment Setup
- Python version: `>=3.10`.
- Editable install: `python -m pip install -e .`
- Dev install: `python -m pip install -e .[dev]`
- Alternative from README: `uv pip install .`

## 4) Build / Lint / Test Commands

### Run commands
- CLI help: `dataset-insights --help`
- Analyze help: `dataset-insights analyze --help`
- Run analysis: `dataset-insights analyze data/sample.csv --outdir reports/`

### Test commands
- Run all: `pytest tests/`
- Quiet all: `pytest tests/ -q`
- Stop early: `pytest tests/ -x`
- Single file: `pytest tests/test_analyze.py`
- Single test (important): `pytest tests/test_analyze.py::test_compute_missingness_values`
- Single CLI test: `pytest tests/test_cli.py::test_analyze_output_files`
- By keyword: `pytest tests/ -k missingness`

### Build commands
- No dedicated build script is configured.
- Optional package build (if `build` is installed): `python -m build`

### Lint/format commands
- No linter/formatter is configured in `pyproject.toml`.
- Do not assume Ruff/Black/Flake8 are required.
- Quality gate here is tests plus readable style.

## 5) Code Style

### Imports
- Use `from __future__ import annotations`.
- Order imports: standard library, third-party, local.
- Use explicit imports; avoid `*` imports.

### Formatting
- Follow PEP 8 conventions.
- Keep functions short and readable.
- Match existing string style (double quotes).
- Add comments only for non-obvious logic.
- Keep docstrings concise and practical.

### Types
- Add type hints for parameters and return values.
- Prefer modern syntax: `str | Path`, `list[dict]`.
- Keep public helper return types explicit.

### Naming
- `snake_case` for functions/variables.
- `UPPER_SNAKE_CASE` for constants.
- Tests named like `test_<behavior>`.
- Use descriptive names; short local names like `df`, `ax` are fine.

### Pandas and data handling
- Prefer vectorized pandas ops (`isna`, `sum`, `describe`, `corr`).
- Use `pathlib.Path` for paths.
- Keep transformations explicit and local.
- Avoid global mutable state.
- Preserve output schema unless required to change.

### CLI conventions
- Use Click (`click.echo`) for user-facing text.
- Keep console output concise and informative.
- Preserve skip messaging style (`Skipped: ...`).
- Keep non-zero exits for invalid user input/data.

### Error handling
- Use clear error messages for user/data issues.
- Existing fatal-load pattern in `analyze.py`:
  - print to stderr
  - exit with `sys.exit(1)`
- Avoid noisy stack traces for expected bad input.
- Catch specific exceptions when possible.

## 6) Testing Guidelines
- Add fixtures in `tests/conftest.py` when reusable.
- Put analysis logic tests in `tests/test_analyze.py`.
- Put CLI behavior/file-output tests in `tests/test_cli.py`.
- For behavior changes, update/add nearest tests.
- Use `tmp_path` for filesystem isolation.
- Keep tests deterministic.

Recommended verification flow:
1. Run the most targeted single test.
2. Run the related test file.
3. Run full suite: `pytest tests/`.

## 7) Output File Contract
- Keep stable output names unless task says otherwise:
  - `summary.md`
  - `summary_statistics.csv`
  - `schema.json`
  - `missingness.csv`
  - `correlation.csv`
  - `plots/distribution_histogram.png`
  - `plots/correlation_heatmap.png`
  - `plots/missingness_bar.png`
- Writers/plotters should return output `Path`.
- Ensure output dirs exist with `mkdir(parents=True, exist_ok=True)`.

## 8) Documentation Rules
- Update `README.md` for user-visible behavior changes.
- Keep docs aligned with actual command output and files.
- Do not document unimplemented features.

## 9) Dependency and Change Hygiene
- Keep diffs focused on requested work.
- Avoid unrelated code churn.
- Do not add dependencies unless necessary.
- If adding one, update `pyproject.toml` and explain why.

## 10) Git Hygiene for Agents
- Avoid touching unrelated files.
- Do not rewrite history unless explicitly requested.
- Keep commits (when requested) coherent and reviewable.

## 11) Cursor/Copilot Rule Files
Checked for additional instruction files:
- `.cursor/rules/`: not present
- `.cursorrules`: not present
- `.github/copilot-instructions.md`: not present

No extra Cursor/Copilot instructions are currently present in this repo.

## 12) Quick Checklist
- Read relevant source + tests before editing.
- Implement smallest acceptable change.
- Add/update tests when behavior changes.
- Run targeted test(s), then broader suite.
- Update docs if user-facing behavior changed.
- Keep patch simple and maintainable.
