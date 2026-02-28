"""CLI integration tests."""

from __future__ import annotations

from pathlib import Path

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
    assert (outdir / "plots" / "distribution_histogram.png").exists()
    assert (outdir / "plots" / "correlation_heatmap.png").exists()
    assert (outdir / "plots" / "missingness_bar.png").exists()


def test_empty_csv(runner, empty_csv, tmp_path):
    """Graceful error message and non-zero exit on an empty CSV."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(empty_csv), "--outdir", str(outdir)])
    assert result.exit_code != 0
    assert "empty" in result.output.lower() or "Error" in result.output


def test_no_numeric_columns(runner, no_numeric_csv, tmp_path):
    """Runs successfully on a CSV with no numeric columns; skips histogram/heatmap."""
    outdir = tmp_path / "reports"
    result = runner.invoke(main, ["analyze", str(no_numeric_csv), "--outdir", str(outdir)])
    assert result.exit_code == 0
    # missingness bar is always generated
    assert (outdir / "plots" / "missingness_bar.png").exists()
    # histogram and heatmap should be skipped
    assert not (outdir / "plots" / "distribution_histogram.png").exists()
    assert not (outdir / "plots" / "correlation_heatmap.png").exists()
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
