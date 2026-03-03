"""Report writers for markdown, CSV, and JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .analyze import QualityIssue


def _issue_to_dict(issue: QualityIssue | dict[str, Any]) -> dict[str, Any]:
    if isinstance(issue, QualityIssue):
        return issue.to_dict()
    return {
        "rule": str(issue.get("rule", "")),
        "severity": str(issue.get("severity", "info")),
        "column": issue.get("column"),
        "count": int(issue.get("count", 0)),
        "pct": float(issue.get("pct", 0.0)),
        "examples": [str(v) for v in issue.get("examples", [])],
        "message": str(issue.get("message", "")),
        "suggestion": str(issue.get("suggestion", "")),
    }


def _build_insights_section(
    summary: dict,
    missingness: pd.DataFrame | None,
    duplicates: dict[str, Any] | None,
    outliers: pd.DataFrame | None,
    quality_issues: list[QualityIssue] | None,
) -> list[str]:
    rows = int(summary["shape"]["rows"])
    cols = int(summary["shape"]["columns"])
    lines: list[str] = ["### Dataset Overview"]
    lines.append(
        f"This dataset contains {rows:,} rows and {cols} columns. "
        "Detailed numeric statistics are in summary_statistics.csv."
    )

    lines.append("\n### Missing Data")
    if missingness is None or missingness.empty:
        lines.append("Missingness summary is not available in this run.")
    else:
        missing_counts = missingness["missing_count"].to_numpy(dtype="int64")
        total_missing = int(missing_counts.sum())
        cols_with_missing = int((missing_counts > 0).sum())
        if cols_with_missing == 0:
            lines.append("No missing values were detected across all columns.")
        else:
            missing_only = missingness[missingness["missing_count"] > 0].reset_index(drop=True)
            top_col = str(missing_only.loc[0, "column"])
            top_pct = float(missing_only.loc[0, "missing_pct"])
            if len(missing_only) > 1:
                second_col = str(missing_only.loc[1, "column"])
                second_pct = float(missing_only.loc[1, "missing_pct"])
                lines.append(
                    f"{cols_with_missing} out of {cols} columns have missing values "
                    f"({total_missing:,} missing values total). "
                    f"The most affected columns are `{top_col}` ({top_pct:.2f}%) and "
                    f"`{second_col}` ({second_pct:.2f}%)."
                )
            else:
                lines.append(
                    f"{cols_with_missing} out of {cols} columns have missing values "
                    f"({total_missing:,} missing values total). "
                    f"The most affected column is `{top_col}` ({top_pct:.2f}%)."
                )
            lines.append("See missingness.csv for the full per-column breakdown.")

    lines.append("\n### Duplicate Rows")
    if duplicates is None:
        lines.append("Duplicate summary is not available in this run.")
    else:
        duplicate_rows = int(duplicates.get("duplicate_rows_excluding_first", 0))
        duplicate_groups = int(duplicates.get("duplicate_group_count", 0))
        duplicate_pct = float(duplicates.get("duplicate_row_pct", 0.0))
        shown_examples = len(duplicates.get("example_rows", []))
        omitted_count = int(duplicates.get("omitted_count", 0))
        if duplicate_rows == 0:
            lines.append("No duplicate rows were detected.")
        else:
            lines.append(
                f"In this dataset, {duplicate_rows:,} rows are exact copies of a row that "
                f"already appeared earlier. These duplicates come from {duplicate_groups:,} "
                f"distinct repeated patterns, making up {duplicate_pct:.2f}% of all rows. "
                f"Here are {shown_examples} example duplicate rows in duplicates.csv; "
                f"the other {omitted_count:,} are not shown."
            )

    lines.append("\n### Outliers (IQR Method)")
    if outliers is None or outliers.empty:
        lines.append("No numeric outlier summary is available for this run.")
    else:
        flagged = outliers[outliers["outlier_count"] > 0].copy()
        if flagged.empty:
            lines.append("No outliers were detected with the IQR method.")
        else:
            flagged = flagged.sort_values("outlier_pct", ascending=False).reset_index(drop=True)
            top = flagged.head(3)
            highlights = []
            for _, row in top.iterrows():
                highlights.append(
                    f"`{row['column']}` has {int(row['outlier_count']):,} outliers "
                    f"({float(row['outlier_pct']):.2f}%)"
                )
            lines.append(
                f"{len(flagged)} numeric columns have IQR outliers. Top columns by outlier rate: "
                f"{'; '.join(highlights)}. See outliers.csv for full bounds and counts."
            )

    lines.append("\n### Data Quality Issues")
    issue_dicts = [_issue_to_dict(issue) for issue in (quality_issues or [])]
    if not issue_dicts:
        lines.append("No data quality issues were flagged.")
    else:
        counts = {"critical": 0, "warn": 0, "info": 0}
        for issue in issue_dicts:
            severity = str(issue["severity"])
            if severity in counts:
                counts[severity] += 1
        lines.append(
            f"{counts['critical']} critical, {counts['warn']} warning(s), and "
            f"{counts['info']} info issue(s) were flagged."
        )
        for issue in issue_dicts[:5]:
            prefix = f"`{issue['column']}`: " if issue.get("column") else ""
            lines.append(f"- {prefix}{issue['message']}")
        lines.append("See data_quality.json for complete issue details and parseability metrics.")

    return lines


def write_summary_md(
    summary: dict,
    outdir: Path,
    quality_issues: list[QualityIssue] | None = None,
    missingness: pd.DataFrame | None = None,
    duplicates: dict[str, Any] | None = None,
    outliers: pd.DataFrame | None = None,
) -> Path:
    """Write a concise dataset overview to summary.md."""
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

    lines.append("\n## Insights\n")
    lines.extend(
        _build_insights_section(
            summary=summary,
            missingness=missingness,
            duplicates=duplicates,
            outliers=outliers,
            quality_issues=quality_issues,
        )
    )

    issues = quality_issues or []
    lines.append("\n## Data Quality Warnings\n")
    if not issues:
        lines.append("_No data quality issues flagged._")
    else:
        issue_dicts = [_issue_to_dict(issue) for issue in issues]
        for severity, title in (("critical", "Critical"), ("warn", "Warnings"), ("info", "Info")):
            scoped = [i for i in issue_dicts if i["severity"] == severity]
            if not scoped:
                continue
            lines.append(f"### {title}")
            for issue in scoped:
                prefix = f"`{issue['column']}`: " if issue.get("column") else ""
                lines.append(f"- {prefix}{issue['message']}")

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
    stats_keys = ["count", "mean", "std", "min", "25%", "50%", "75%", "max", "skewness"]

    rows = []
    for col, stats in numeric_summary.items():
        row = {"column": col}
        for key in stats_keys:
            value = stats.get(key, "")
            row[key] = "" if value is None else value
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


def write_duplicates_csv(duplicates: dict[str, Any], outdir: Path) -> Path:
    """Write duplicate-row summary plus capped example rows to duplicates.csv."""
    outdir.mkdir(parents=True, exist_ok=True)

    total_rows = int(duplicates.get("total_rows", 0))
    duplicate_rows = int(duplicates.get("duplicate_rows_excluding_first", 0))
    duplicate_groups = int(duplicates.get("duplicate_group_count", 0))
    duplicate_pct = float(duplicates.get("duplicate_row_pct", 0.0))
    example_limit = int(duplicates.get("example_limit", 0))
    omitted_count = int(duplicates.get("omitted_count", 0))
    truncated = bool(duplicates.get("truncated", False))
    example_rows = duplicates.get("example_rows", [])

    rows: list[dict[str, Any]] = [
        {
            "record_type": "summary",
            "total_rows": total_rows,
            "duplicate_rows_excluding_first": duplicate_rows,
            "duplicate_group_count": duplicate_groups,
            "duplicate_row_pct": duplicate_pct,
            "example_limit": example_limit,
            "omitted_count": omitted_count,
            "truncated": truncated,
            "example_index": "",
            "example_row_json": "",
        }
    ]

    for idx, example in enumerate(example_rows, start=1):
        rows.append(
            {
                "record_type": "example",
                "total_rows": total_rows,
                "duplicate_rows_excluding_first": duplicate_rows,
                "duplicate_group_count": duplicate_groups,
                "duplicate_row_pct": duplicate_pct,
                "example_limit": example_limit,
                "omitted_count": omitted_count,
                "truncated": truncated,
                "example_index": idx,
                "example_row_json": json.dumps(example),
            }
        )

    out_path = outdir / "duplicates.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False)
    return out_path


def write_outliers_csv(outliers: pd.DataFrame, outdir: Path) -> Path:
    """Write IQR outlier analysis to outliers.csv."""
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "outliers.csv"
    outliers.to_csv(out_path, index=False)
    return out_path


def write_data_quality_json(
    issues: list[QualityIssue],
    parseability: pd.DataFrame,
    duplicates: dict[str, Any],
    outdir: Path,
) -> Path:
    """Write consolidated quality findings to data_quality.json."""
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "data_quality.json"

    duplicate_summary = {
        "total_rows": int(duplicates.get("total_rows", 0)),
        "duplicate_rows_excluding_first": int(
            duplicates.get("duplicate_rows_excluding_first", 0)
        ),
        "duplicate_group_count": int(duplicates.get("duplicate_group_count", 0)),
        "duplicate_row_pct": float(duplicates.get("duplicate_row_pct", 0.0)),
        "example_limit": int(duplicates.get("example_limit", 0)),
        "omitted_count": int(duplicates.get("omitted_count", 0)),
        "truncated": bool(duplicates.get("truncated", False)),
        "example_rows": duplicates.get("example_rows", []),
    }

    payload = {
        "duplicates": duplicate_summary,
        "issues": [_issue_to_dict(issue) for issue in issues],
        "parseability": parseability.to_dict(orient="records"),
    }

    out_path.write_text(json.dumps(payload, indent=2))
    return out_path
