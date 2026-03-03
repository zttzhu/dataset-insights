"""CLI integration tests."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from dataset_insights.cli import main


@pytest.fixture()
def runner():
    return CliRunner()


def test_cli_help(runner):
    """--help exits 0 and prints usage text."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_analyze_help(runner):
    """analyze --help exits 0 and prints usage text."""
    result = runner.invoke(main, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "CSV_PATH" in result.output


def test_analyze_output_files(runner, sample_csv, tmp_path):
    """All expected output files are created for a valid CSV."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(sample_csv), "--outdir", str(outdir)])
    assert result.exit_code == 0, f"CLI failed:\n{result.output}"

    assert (outdir / "summary.md").exists()
    assert (outdir / "summary_statistics.csv").exists()
    assert (outdir / "schema.json").exists()
    assert (outdir / "missingness.csv").exists()
    assert (outdir / "correlation.csv").exists()
    assert (outdir / "duplicates.csv").exists()
    assert (outdir / "outliers.csv").exists()
    assert (outdir / "data_quality.json").exists()
    assert (outdir / "plots" / "distribution_histogram.png").exists()
    assert (outdir / "plots" / "correlation_heatmap.png").exists()
    assert (outdir / "plots" / "missingness_bar.png").exists()
    assert (outdir / "plots" / "box_plot.png").exists()

    summary_md = (outdir / "summary.md").read_text()
    assert "## Insights" in summary_md
    assert "### Duplicate Rows" in summary_md


def test_summary_md_duplicate_insight_text(runner, duplicates_csv, tmp_path):
    """summary.md should include a plain-English duplicate summary sentence."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(duplicates_csv), "--outdir", str(outdir)])
    assert result.exit_code == 0

    summary_md = (outdir / "summary.md").read_text()
    assert "rows are exact copies of a row that already appeared earlier" in summary_md
    assert "distinct repeated patterns" in summary_md
    assert "are not shown" in summary_md


def test_empty_csv(runner, empty_csv, tmp_path):
    """Graceful error message and non-zero exit on an empty CSV."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(empty_csv), "--outdir", str(outdir)])
    assert result.exit_code != 0
    assert "empty" in result.output.lower() or "Error" in result.output


def test_no_numeric_columns(runner, no_numeric_csv, tmp_path):
    """Runs successfully on a CSV with no numeric columns; skips numeric-only plots."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(no_numeric_csv), "--outdir", str(outdir)])
    assert result.exit_code == 0
    assert (outdir / "plots" / "missingness_bar.png").exists()
    assert not (outdir / "plots" / "distribution_histogram.png").exists()
    assert not (outdir / "plots" / "correlation_heatmap.png").exists()
    assert not (outdir / "plots" / "box_plot.png").exists()
    assert "Skipped" in result.output


def test_cli_suspicious_summary_caps_examples(runner, tmp_path):
    """CLI should print a compact suspicious-value audit with capped examples."""
    csv_path = tmp_path / "suspicious.csv"
    csv_path.write_text(
        "id,department\n"
        "1,??missing\n"
        "2,lost??\n"
        "3,???unknown???\n"
        "4,--none--\n"
        "5,??null??\n"
    )
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(csv_path), "--outdir", str(outdir)])

    assert result.exit_code == 0
    assert "Suspicious values treated as missing:" in result.output
    assert "department: 5 values" in result.output
    assert "'??missing'" in result.output
    assert "'lost??'" in result.output
    assert "'???unknown???'" in result.output
    assert "'--none--'" not in result.output


def test_cli_quality_warnings(runner, duplicates_csv, tmp_path):
    """CLI should print a quality issue summary when checks flag issues."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(duplicates_csv), "--outdir", str(outdir)])

    assert result.exit_code == 0
    assert "Quality issues:" in result.output
    assert "WARN" in result.output
