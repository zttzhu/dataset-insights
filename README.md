# dataset-insights

Instant CSV dataset orientation from the command line. Drop any `.csv` and get:

- **summary.md** — shape, dtypes, and quality warning summary
- **summary_statistics.csv** — numeric descriptive stats including skewness
- **schema.json** — per-column metadata (type, unique count, sample values)
- **missingness.csv** — missing value audit per column
- **duplicates.csv** and **outliers.csv** — duplicate-row and IQR outlier diagnostics
- **data_quality.json** — consolidated quality flags + parseability rates
- **4 diagnostic plots** — histograms, correlation heatmap, missingness bar, box plot

---

## Quickstart

```bash
# Install (editable mode)
pip install -e .
# or with uv
uv pip install .

# Run
dataset-insights analyze data/sample.csv --outdir reports/

# Help
dataset-insights --help
dataset-insights analyze --help
```

---

## Example Output

```
Loading data/sample.csv ...
  1,000 rows x 12 columns

Writing reports ...
  reports/summary.md
  reports/summary_statistics.csv
  reports/schema.json
  reports/missingness.csv
  reports/correlation.csv
  reports/duplicates.csv
  reports/outliers.csv
  reports/data_quality.json

Generating plots ...
  reports/plots/distribution_histogram.png
  reports/plots/correlation_heatmap.png
  reports/plots/missingness_bar.png
  reports/plots/box_plot.png

Done. 4/12 columns have missing data (87 total missing values).
Quality issues: 0 critical, 2 warnings, 1 info.
Output written to: /home/user/project/reports/
```

---

## Output Files

| File | Description |
|------|-------------|
| `reports/summary.md` | Dataset shape, column dtypes, and grouped quality warnings |
| `reports/summary_statistics.csv` | Numeric descriptive stats: `count`, `mean`, `std`, `min`, `25%`, `50%`, `75%`, `max`, `skewness` |
| `reports/schema.json` | JSON array: column name, dtype, unique count, missing count, sample values |
| `reports/missingness.csv` | Sorted by missing %, columns: `column`, `missing_count`, `missing_pct` |
| `reports/correlation.csv` | Full Pearson correlation matrix for numeric columns (if 2+ numeric columns) |
| `reports/duplicates.csv` | Duplicate summary and capped duplicate-row examples (`truncated` and `omitted_count` included) |
| `reports/outliers.csv` | IQR-based outlier metrics per numeric column (`q1`, `q3`, `iqr`, bounds, count, pct) |
| `reports/data_quality.json` | Consolidated quality issues, parseability rates, and duplicate summary |
| `reports/plots/distribution_histogram.png` | Histograms for up to 6 numeric columns |
| `reports/plots/correlation_heatmap.png` | Pearson correlation heatmap for numeric columns |
| `reports/plots/missingness_bar.png` | Bar chart of missing % per column |
| `reports/plots/box_plot.png` | Box plots for up to 6 numeric columns (prioritized by outlier rate) |

---

## Quality Checks

Beyond missing-value detection, `dataset-insights` performs broad, domain-agnostic quality checks:

- Blank and duplicate column names from the raw CSV header
- Duplicate-row metrics with explicit semantics (`duplicate_rows_excluding_first`)
- IQR outlier detection with guardrails for sparse columns
- High-missing column detection (`high_missing`) with thresholds (`warn` >= 20%, `critical` >= 50%)
- Constant-column, high-cardinality, and leading/trailing whitespace detection
- Parseability rates for object columns (`numeric_parse_pct`, `datetime_parse_pct`)
- Mixed-type warnings when a text column is partially numeric (with conservative thresholds)

---

## Missing Value Placeholders

Messy placeholder cells are treated as missing in two passes:

1) **Exact-token parsing at CSV load** via `na_values`.
2) **Whole-cell normalization after load** for wrapped tokens.

Normalization rules:

- trim whitespace
- lowercase
- strip leading/trailing wrapper punctuation: `? ! . * - _ ~ #`
- treat punctuation-only cells as missing (for example: `??`, `---`, `...`)
- match normalized whole-cell keywords only (no broad substring matching)

Default placeholder keywords (case-insensitive after normalization):

- `missing`, `lost`, `unknown`, `unavailable`, `undefined`
- `not available`, `not applicable`
- `blank`, `empty`, `none`, `null`, `nil`
- `n/a`, `na`, `n.a.`, `n.a`
- `no data`, `no value`, `tbd`, `tba`

Examples that are treated as missing:

- `??`, `????`, `--`, `...`
- `??missing`, `lost??`, `---n/a---`, `  Not Available  `

Examples that are **not** treated as missing:

- `not missing`
- `customer_missing_reason`
- `lost_and_found`

---

## Installation Requirements

- Python 3.10+
- Dependencies installed automatically: `click`, `pandas`, `matplotlib`, `seaborn`

---

## Running Tests

```bash
pip install -e .[dev]
pytest tests/
```

The test suite includes 45 tests covering CSV loading, missing-value detection, duplicate/outlier analysis, quality warnings, and full CLI integration.

---

## Limitations

- **CSV only** — Excel and Parquet are not supported in v1
- **4 plots only** — distribution histogram, correlation heatmap, missingness bar, box plot
- **No interactive dashboards** — outputs are static PNGs and text files
- **Up to 6 columns per chart** for histogram and box plot readability caps
- **Correlation heatmap** requires at least 2 numeric columns

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Project Structure

```
dataset-insights/
├── pyproject.toml
├── README.md
├── AGENTS.md
├── LICENSE
├── data/
│   └── sample.csv         # bundled demo dataset
├── src/
│   └── dataset_insights/
│       ├── __init__.py
│       ├── cli.py          # Click CLI entrypoint
│       ├── analyze.py      # data loading and quality/statistics checks
│       ├── plots.py        # 4 plot generators
│       └── reports.py      # report writers
└── tests/
    ├── conftest.py
    ├── test_cli.py
    └── test_analyze.py
```
