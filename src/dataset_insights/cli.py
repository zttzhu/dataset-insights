"""CLI entrypoint for dataset-insights."""

from __future__ import annotations

from pathlib import Path

import click

from .analyze import (
    QualityIssue,
    coerce_suspicious_to_nan,
    compute_duplicates,
    compute_missingness,
    compute_outliers,
    compute_schema,
    compute_summary,
    detect_column_warnings,
    load_csv,
    summarize_quality_issues,
)
from .plots import (
    plot_box_plots,
    plot_correlation_heatmap,
    plot_distribution_histogram,
    plot_missingness_bar,
)
from .reports import (
    write_correlation_csv,
    write_data_quality_json,
    write_duplicates_csv,
    write_missingness_csv,
    write_outliers_csv,
    write_schema_json,
    write_summary_md,
    write_summary_statistics_csv,
)


@click.group()
@click.version_option(package_name="dataset-insights")
def main():
    """dataset-insights: instant orientation for any CSV dataset."""


@main.command()
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--outdir",
    default="reports",
    show_default=True,
    help="Directory to write output files.",
    type=click.Path(),
)
def analyze(csv_path: str, outdir: str):
    """Analyze a CSV file and write reports + diagnostic plots to OUTDIR."""
    max_examples = 3
    out = Path(outdir)

    click.echo(f"Loading {csv_path} ...")
    df = load_csv(csv_path)
    df, suspicious_audit = coerce_suspicious_to_nan(df)
    click.echo(f"  {df.shape[0]:,} rows x {df.shape[1]} columns")

    if suspicious_audit:
        total_suspicious = 0
        for entry in suspicious_audit.values():
            raw_count = entry.get("count")
            if isinstance(raw_count, int):
                total_suspicious += raw_count
        click.echo(f"  Detected {total_suspicious:,} suspicious values treated as missing")

    # --- Compute ---
    summary = compute_summary(df)
    schema = compute_schema(df)
    missingness = compute_missingness(df)
    duplicates = compute_duplicates(df)
    outliers = compute_outliers(df)
    quality_issues, parseability = detect_column_warnings(df)

    duplicate_count = int(duplicates.get("duplicate_rows_excluding_first", 0))
    duplicate_pct = float(duplicates.get("duplicate_row_pct", 0.0))
    if duplicate_count > 0:
        quality_issues.append(
            QualityIssue(
                rule="duplicate_rows",
                severity="warn",
                column=None,
                count=duplicate_count,
                pct=duplicate_pct,
                examples=[],
                message=(
                    f"Detected {duplicate_count} duplicate row(s) beyond first occurrence "
                    f"({duplicate_pct:.2f}% of rows)."
                ),
                suggestion="Review deduplication logic or enforce primary keys upstream.",
            )
        )

    # --- Write reports ---
    click.echo("\nWriting reports ...")
    p1 = write_summary_md(
        summary,
        out,
        quality_issues=quality_issues,
        missingness=missingness,
        duplicates=duplicates,
        outliers=outliers,
    )
    click.echo(f"  {p1}")

    p1b = write_summary_statistics_csv(summary, out)
    if p1b:
        click.echo(f"  {p1b}")
    else:
        click.echo("  Skipped: summary_statistics.csv (no numeric columns)")

    p2 = write_schema_json(schema, out)
    click.echo(f"  {p2}")

    p3 = write_missingness_csv(missingness, out)
    click.echo(f"  {p3}")

    p3b = write_correlation_csv(df, out)
    if p3b:
        click.echo(f"  {p3b}")
    else:
        click.echo("  Skipped: correlation.csv (fewer than 2 numeric columns)")

    p4 = write_duplicates_csv(duplicates, out)
    click.echo(f"  {p4}")

    p5 = write_outliers_csv(outliers, out)
    click.echo(f"  {p5}")

    p6 = write_data_quality_json(quality_issues, parseability, duplicates, out)
    click.echo(f"  {p6}")

    # --- Generate plots ---
    click.echo("\nGenerating plots ...")
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        click.echo("  Warning: no numeric columns found -- skipping histogram and heatmap.")

    p7 = plot_distribution_histogram(df, out)
    if p7:
        click.echo(f"  {p7}")
    else:
        click.echo("  Skipped: distribution_histogram.png (no numeric columns)")

    p8 = plot_correlation_heatmap(df, out)
    if p8:
        click.echo(f"  {p8}")
    else:
        click.echo("  Skipped: correlation_heatmap.png (fewer than 2 numeric columns)")

    p9 = plot_missingness_bar(df, out)
    click.echo(f"  {p9}")

    p10 = plot_box_plots(df, out, outliers=outliers)
    if p10:
        click.echo(f"  {p10}")
    else:
        click.echo("  Skipped: box_plot.png (no numeric columns)")

    # --- Console summary ---
    missing_count_values = missingness["missing_count"].to_numpy(dtype="int64")
    total_missing = int(missing_count_values.sum())
    cols_with_missing = int((missing_count_values > 0).sum())
    click.echo(
        f"\nDone. {cols_with_missing}/{df.shape[1]} columns have missing data "
        f"({total_missing:,} total missing values)."
    )

    if suspicious_audit:
        click.echo("Suspicious values treated as missing:")
        for column, entry in suspicious_audit.items():
            raw_count = entry.get("count")
            count = raw_count if isinstance(raw_count, int) else 0
            examples_raw = entry["examples"] if isinstance(entry["examples"], list) else []
            examples = [str(v) for v in examples_raw[:max_examples]]
            if examples:
                formatted_examples = ", ".join(repr(v) for v in examples)
                click.echo(f"  {column}: {count} values (e.g. {formatted_examples})")
            else:
                click.echo(f"  {column}: {count} values")

    severity_counts = summarize_quality_issues(quality_issues)
    total_issues = sum(severity_counts.values())
    if total_issues:
        click.echo(
            "Quality issues: "
            f"{severity_counts['critical']} critical, "
            f"{severity_counts['warn']} warnings, "
            f"{severity_counts['info']} info."
        )

        highlighted = [
            issue
            for issue in quality_issues
            if issue.severity in {"critical", "warn"}
        ]
        for issue in highlighted[:8]:
            where = f" [{issue.column}]" if issue.column else ""
            click.echo(f"  {issue.severity.upper()}{where}: {issue.message}")

    click.echo(f"Output written to: {out.resolve()}/")
