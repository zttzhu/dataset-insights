"""Report writers: summary.md, schema.json, missingness.csv."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def write_summary_md(summary: dict, outdir: Path) -> Path:
    """Write a concise dataset overview to summary.md.

    The wide numeric-statistics table is no longer embedded here; it lives in
    ``summary_statistics.csv`` so users can inspect it in a spreadsheet.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "summary.md"

    lines = [
        "# Dataset Summary\n",
        f"**Rows:** {summary['shape']['rows']}  ",
        f"**Columns:** {summary['shape']['columns']}\n",
        "## Column Overview\n",
        "| Column | Type |",
        "|--------|------|",
    ]
    for col, dtype in summary["dtypes"].items():
        lines.append(f"| `{col}` | {dtype} |")

    numeric_summary = summary.get("numeric_summary", {})
    if numeric_summary:
        lines.append(
            "\nDetailed numeric statistics are in "
            "[summary_statistics.csv](summary_statistics.csv)."
        )
    else:
        lines.append("\n_No numeric columns found._")

    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def write_summary_statistics_csv(summary: dict, outdir: Path) -> Path | None:
    """Write per-column numeric statistics to summary_statistics.csv.

    Returns None when there are no numeric columns.
    """
    numeric_summary = summary.get("numeric_summary", {})
    if not numeric_summary:
        return None

    outdir.mkdir(parents=True, exist_ok=True)
    stats_keys = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]

    rows = []
    for col, stats in numeric_summary.items():
        row = {"column": col}
        for key in stats_keys:
            row[key] = stats.get(key, "")
        rows.append(row)

    df = pd.DataFrame(rows, columns=["column"] + stats_keys)
    out_path = outdir / "summary_statistics.csv"
    df.to_csv(out_path, index=False)
    return out_path


def write_schema_json(schema: list[dict], outdir: Path) -> Path:
    """Write column schema metadata to schema.json."""
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "schema.json"
    out_path.write_text(json.dumps(schema, indent=2))
    return out_path


def write_missingness_csv(missingness: pd.DataFrame, outdir: Path) -> Path:
    """Write missingness audit to missingness.csv."""
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "missingness.csv"
    missingness.to_csv(out_path, index=False)
    return out_path


def write_correlation_csv(df: pd.DataFrame, outdir: Path) -> Path | None:
    """Write the full correlation matrix to correlation.csv.

    Returns None if fewer than 2 numeric columns.
    """
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return None

    outdir.mkdir(parents=True, exist_ok=True)
    corr = numeric_df.corr()
    out_path = outdir / "correlation.csv"
    corr.to_csv(out_path)
    return out_path
