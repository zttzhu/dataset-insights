"""Unit tests for analyze.py functions."""

from __future__ import annotations

import pandas as pd
import pytest

from dataset_insights.analyze import (
    coerce_suspicious_to_nan,
    compute_missingness,
    compute_schema,
    compute_summary,
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


def test_compute_summary_shape(sample_csv):
    df = load_csv(sample_csv)
    summary = compute_summary(df)
    assert summary["shape"]["rows"] == 10
    assert summary["shape"]["columns"] == 5


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
    assert len(audit["token"]["examples"]) == 1


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
