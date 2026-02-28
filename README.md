# dataset-insights

Instant CSV dataset orientation from the command line. Drop any `.csv` and get:

- **summary.md** — shape, dtypes, and descriptive statistics
- **schema.json** — per-column metadata (type, unique count, sample values)
- **missingness.csv** — missing value audit per column
- **3 diagnostic plots** — histograms, correlation heatmap, missingness bar chart

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
  reports/schema.json
  reports/missingness.csv

Generating plots ...
  reports/plots/distribution_histogram.png
  reports/plots/correlation_heatmap.png
  reports/plots/missingness_bar.png

Done. 4/12 columns have missing data (87 total missing values).
Output written to: /home/user/project/reports/
```

---

## Output Files

| File | Description |
|------|-------------|
| `reports/summary.md` | Dataset shape, column dtypes, and descriptive stats for numeric columns |
| `reports/schema.json` | JSON array: column name, dtype, unique count, missing count, sample values |
| `reports/missingness.csv` | Sorted by missing %, columns: `column`, `missing_count`, `missing_pct` |
| `reports/plots/distribution_histogram.png` | Histograms for up to 6 numeric columns |
| `reports/plots/correlation_heatmap.png` | Pearson correlation heatmap for numeric columns |
| `reports/plots/missingness_bar.png` | Bar chart of missing % per column |

---

## Missing Value Placeholders

`dataset-insights` now treats messy placeholder cells as missing in two passes:

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
pip install pytest
pytest tests/
```

Test coverage:

| Test | Checks |
|------|--------|
| `test_cli_help` | `--help` exits 0, prints usage |
| `test_analyze_output_files` | All 6 output files created |
| `test_empty_csv` | Graceful error on empty input |
| `test_missingness_values` | Missingness counts match expected values |

---

## Limitations

- **CSV only** — Excel and Parquet are not supported in v1
- **3 plots only** — distribution histogram, correlation heatmap, missingness bar
- **No interactive dashboards** — outputs are static PNGs and text files
- **Up to 6 subplots** in the histogram (top 6 numeric columns by column order)
- **Correlation heatmap** requires at least 2 numeric columns

---

## Project Structure

```
dataset-insights/
├── pyproject.toml
├── README.md
├── src/
│   └── dataset_insights/
│       ├── cli.py        # click CLI entrypoint
│       ├── analyze.py    # data loading and statistics
│       ├── plots.py      # 3 plot generators
│       └── reports.py    # report file writers
├── tests/
│   ├── conftest.py
│   ├── test_cli.py
│   └── test_analyze.py
└── data/                 # place your CSV files here
```
