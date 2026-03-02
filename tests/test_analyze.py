"""Unit tests for analyze.py functions."""

from __future__ import annotations

import pandas as pd
import pytest

from dataset_insights.analyze import (
    coerce_suspicious_to_nan,
    compute_duplicates,
    compute_missingness,
    compute_outliers,
    compute_schema,
    compute_summary,
    detect_column_warnings,
    load_csv,
)


def test_load_csv_valid(sample_csv):
    df = load_csv(sample_csv)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (10, 5)


def test_load_csv_empty_exits(empty_csv):
    with pytest.raises(SystemExit) as exc_info:
        load_csv(empty_csv)
    assert exc_info.value.code != 0


def test_load_csv_missing_file(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        load_csv(tmp_path / "nonexistent.csv")
    assert exc_info.value.code != 0


def test_load_csv_header_issues_detected(blank_colname_csv):
    df = load_csv(blank_colname_csv)
    issues = df.attrs.get("header_issues", [])
    rules = {issue.rule for issue in issues}
    assert "blank_column_names" in rules
    assert "duplicate_column_names" in rules


def test_compute_summary_shape(sample_csv):
    df = load_csv(sample_csv)
    summary = compute_summary(df)
    assert summary["shape"]["rows"] == 10
    assert summary["shape"]["columns"] == 5


def test_compute_summary_includes_skewness(sample_csv):
    df = load_csv(sample_csv)
    summary = compute_summary(df)
    numeric_summary = summary["numeric_summary"]
    assert numeric_summary
    for stats in numeric_summary.values():
        assert "skewness" in stats


def test_compute_schema_columns(sample_csv):
    df = load_csv(sample_csv)
    schema = compute_schema(df)
    cols = [entry["column"] for entry in schema]
    assert set(cols) == {"id", "age", "salary", "department", "score"}


def test_compute_missingness_values(sample_csv):
    """Missingness counts must match the known values in the fixture CSV."""
    df = load_csv(sample_csv)
    miss = compute_missingness(df)
    miss_dict = dict(zip(miss["column"], miss["missing_count"]))

    # From the fixture:
    # age: row 3 is missing -> 1
    # score: rows 2, 6, 8 are missing -> 3
    # department: row 4 is missing -> 1
    # salary, id: fully populated -> 0
    assert miss_dict["age"] == 1
    assert miss_dict["score"] == 3
    assert miss_dict["department"] == 1
    assert miss_dict["salary"] == 0
    assert miss_dict["id"] == 0


def test_compute_missingness_pct(sample_csv):
    df = load_csv(sample_csv)
    miss = compute_missingness(df)
    miss_dict = dict(zip(miss["column"], miss["missing_pct"]))
    # score has 3/10 = 30%
    assert abs(miss_dict["score"] - 30.0) < 0.01


def test_compute_missingness_sorted(sample_csv):
    df = load_csv(sample_csv)
    miss = compute_missingness(df)
    pcts = miss["missing_pct"].tolist()
    assert pcts == sorted(pcts, reverse=True)


def test_load_csv_latin1(latin1_csv):
    """load_csv should fall back to latin-1 when UTF-8 decoding fails."""
    df = load_csv(latin1_csv)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (2, 2)
    assert "£" in df["price"].iloc[0]


def test_load_csv_extra_na_values(messy_csv):
    """Known placeholder tokens should be parsed as NaN at CSV load time."""
    df = load_csv(messy_csv)
    assert pd.isna(df.loc[0, "department"])  # ??
    assert pd.isna(df.loc[1, "score"])  # missing
    assert pd.isna(df.loc[6, "score"])  # --


def test_coerce_suspicious_to_nan_detects_wrapped_keywords(messy_csv):
    """Wrapped placeholders such as '??missing' and 'lost??' are coerced to NaN."""
    df = load_csv(messy_csv)
    assert not pd.isna(df.loc[3, "department"])
    assert not pd.isna(df.loc[4, "department"])

    cleaned, audit = coerce_suspicious_to_nan(df)

    assert pd.isna(cleaned.loc[3, "department"])
    assert pd.isna(cleaned.loc[4, "department"])
    assert "department" in audit
    assert audit["department"]["count"] == 2


def test_coerce_suspicious_audit_is_compact():
    """Audit keeps a count with capped unique examples."""
    df = pd.DataFrame({"token": ["??missing", "??missing", "lost??", "lost??", "lost??"]})
    _, audit = coerce_suspicious_to_nan(df, max_examples=1)

    assert audit["token"]["count"] == 5
    examples = audit["token"]["examples"]
    assert isinstance(examples, list)
    assert len(examples) == 1


def test_coerce_suspicious_false_positives(false_positive_csv):
    """Phrase-level text containing keywords should not be over-flagged."""
    df = load_csv(false_positive_csv)
    cleaned, audit = coerce_suspicious_to_nan(df)

    assert cleaned["description"].isna().sum() == 0
    assert cleaned["category"].isna().sum() == 0
    assert cleaned["status"].isna().sum() == 0
    assert audit == {}


def test_compute_missingness_with_suspicious(messy_csv):
    """compute_missingness should include suspicious placeholders defensively."""
    df = load_csv(messy_csv)
    miss = compute_missingness(df)
    miss_dict = dict(zip(miss["column"], miss["missing_count"]))

    assert miss_dict["department"] == 4
    assert miss_dict["score"] == 3
    assert miss_dict["age"] == 1


def test_compute_missingness_false_positive_safety():
    """Defensive coercion should not treat normal phrases as missing."""
    df = pd.DataFrame(
        {
            "notes": [
                "not missing",
                "customer_missing_reason",
                "lost_and_found",
                "available",
                "??missing",
            ]
        }
    )
    miss = compute_missingness(df)
    miss_dict = dict(zip(miss["column"], miss["missing_count"]))
    assert miss_dict["notes"] == 1


def test_compute_duplicates_count_and_cap(duplicates_csv):
    df = load_csv(duplicates_csv)
    duplicates = compute_duplicates(df, max_examples=2)

    assert duplicates["total_rows"] == 6
    assert duplicates["duplicate_rows_excluding_first"] == 3
    assert duplicates["duplicate_group_count"] == 2
    assert abs(duplicates["duplicate_row_pct"] - 50.0) < 0.01
    assert len(duplicates["example_rows"]) == 2
    assert duplicates["truncated"] is True
    assert duplicates["omitted_count"] == 1


def test_compute_duplicates_none(sample_csv):
    df = load_csv(sample_csv)
    duplicates = compute_duplicates(df)
    assert duplicates["duplicate_rows_excluding_first"] == 0
    assert duplicates["duplicate_group_count"] == 0
    assert duplicates["duplicate_row_pct"] == 0.0
    assert duplicates["example_rows"] == []
    assert duplicates["truncated"] is False


def test_compute_outliers_iqr(outliers_csv):
    df = load_csv(outliers_csv)
    outliers = compute_outliers(df)
    row = outliers[outliers["column"] == "value"].iloc[0]
    assert int(row["outlier_count"]) == 1
    assert float(row["outlier_pct"]) > 0
    assert float(row["upper_bound"]) < 200.0


def test_compute_outliers_skip_sparse():
    df = pd.DataFrame({"sparse": [1.0, 2.0, 3.0, None, None]})
    outliers = compute_outliers(df)
    assert outliers.empty


def test_compute_outliers_no_numeric(no_numeric_csv):
    df = load_csv(no_numeric_csv)
    outliers = compute_outliers(df)
    assert outliers.empty


def test_detect_constant_column(constant_col_csv):
    df = load_csv(constant_col_csv)
    issues, _ = detect_column_warnings(df)

    issue = next(i for i in issues if i.rule == "constant_column" and i.column == "constant")
    assert issue.severity == "warn"


def test_detect_high_cardinality(high_cardinality_csv):
    df = load_csv(high_cardinality_csv)
    issues, _ = detect_column_warnings(df)

    issue = next(i for i in issues if i.rule == "high_cardinality_column")
    assert issue.column == "session_key"
    assert issue.severity == "info"


def test_detect_high_cardinality_false_positive(high_cardinality_csv):
    df = load_csv(high_cardinality_csv)
    issues, _ = detect_column_warnings(df)
    flagged = {i.column for i in issues if i.rule == "high_cardinality_column"}
    assert flagged == {"session_key"}


def test_detect_mixed_types(mixed_type_csv):
    df = load_csv(mixed_type_csv)
    issues, _ = detect_column_warnings(df)

    issue = next(i for i in issues if i.rule == "mixed_type_numeric_text")
    assert issue.column == "amount"
    assert issue.severity == "warn"


def test_detect_mixed_types_false_positive():
    df = pd.DataFrame({"amount": ["100", "200", "300"]})
    issues, _ = detect_column_warnings(df)

    assert not any(i.rule == "mixed_type_numeric_text" for i in issues)
    assert any(i.rule == "convertible_numeric_text" for i in issues)


def test_detect_whitespace(whitespace_csv):
    df = load_csv(whitespace_csv)
    issues, _ = detect_column_warnings(df)

    issue = next(i for i in issues if i.rule == "leading_trailing_whitespace")
    assert issue.column == "city"
    assert issue.count == 2


def test_detect_parseability_rates(mixed_type_csv):
    df = load_csv(mixed_type_csv)
    _, parseability = detect_column_warnings(df)
    row = parseability[parseability["column"] == "amount"].iloc[0]
    assert abs(float(row["numeric_parse_pct"]) - 83.33) < 0.1
    assert int(row["numeric_parseable_count"]) == 5


def test_detect_partial_parseability_issue():
    df = pd.DataFrame({"event_time": ["2024-01-01", "2024-03-01", "bad", "maybe"]})
    issues, _ = detect_column_warnings(df)
    assert any(i.rule == "partial_parseability" and i.column == "event_time" for i in issues)


def test_large_dataset_smoke():
    rows = 10_000
    df = pd.DataFrame(
        {
            "id": range(rows),
            "value": [i % 100 for i in range(rows)],
            "token": [str(i) for i in range(rows)],
        }
    )

    summary = compute_summary(df)
    missingness = compute_missingness(df)
    duplicates = compute_duplicates(df)
    outliers = compute_outliers(df)
    issues, parseability = detect_column_warnings(df)

    assert summary["shape"]["rows"] == rows
    assert not missingness.empty
    assert duplicates["duplicate_rows_excluding_first"] == 0
    assert isinstance(outliers, pd.DataFrame)
    assert isinstance(issues, list)
    assert isinstance(parseability, pd.DataFrame)
