"""Core analysis functions: load, validate, and compute stats from a CSV."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import cast

import pandas as pd


EXTRA_NA_VALUES = [
    "?",
    "??",
    "???",
    "????",
    "?????",
    "-",
    "--",
    "---",
    ".",
    "..",
    "...",
    "*",
    "**",
    "***",
    "missing",
    "lost",
    "unknown",
    "unavailable",
    "not available",
    "not applicable",
    "undefined",
    "blank",
    "empty",
    "nil",
    "none",
    "n/a",
    "n.a.",
    "na",
    "n.a",
    "no data",
    "no value",
    "tbd",
    "tba",
]

SUSPICIOUS_KEYWORDS = frozenset(
    {
        "missing",
        "lost",
        "unknown",
        "unavailable",
        "undefined",
        "not available",
        "not applicable",
        "blank",
        "empty",
        "nil",
        "none",
        "null",
        "n/a",
        "na",
        "n.a.",
        "n.a",
        "no data",
        "no value",
        "tbd",
        "tba",
    }
)

PLACEHOLDER_CHARS = "?!.*-_~#"
_PUNCT_ONLY_TOKEN = "__punct_only__"
_PUNCT_ONLY_RE = re.compile(rf"^[{re.escape(PLACEHOLDER_CHARS)}\s]+$")


def _normalize_missing_candidate(value: object) -> str | None:
    """Normalize a cell for whole-value suspicious token matching."""
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    if not stripped:
        return None

    lowered = stripped.lower()
    if _PUNCT_ONLY_RE.fullmatch(lowered):
        return _PUNCT_ONLY_TOKEN

    core = lowered.strip(PLACEHOLDER_CHARS + " ")
    if not core:
        return _PUNCT_ONLY_TOKEN

    return re.sub(r"\s+", " ", core)


def _is_suspicious_keyword(value: object) -> bool:
    return isinstance(value, str) and value in SUSPICIOUS_KEYWORDS


def coerce_suspicious_to_nan(
    df: pd.DataFrame, max_examples: int = 5
) -> tuple[pd.DataFrame, dict[str, dict[str, int | list[str]]]]:
    """Coerce suspicious placeholder tokens to missing values.

    Returns:
        (cleaned_df, audit) where audit is:
        {column: {"count": <int>, "examples": [<unique_examples>]}}
    """
    cleaned = df.copy()
    audit: dict[str, dict[str, int | list[str]]] = {}

    text_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        series = cast(pd.Series, cleaned[col])
        normalized = series.map(_normalize_missing_candidate)
        mask = normalized.eq(_PUNCT_ONLY_TOKEN) | normalized.map(_is_suspicious_keyword)
        mask_series = pd.Series(mask, index=series.index, dtype=bool)
        flagged_count = int(mask_series.to_numpy(dtype=bool).sum())
        if flagged_count == 0:
            continue

        examples: list[str] = []
        seen: set[str] = set()
        for value in series.loc[mask_series].tolist():
            as_text = str(value)
            if as_text in seen:
                continue
            seen.add(as_text)
            examples.append(as_text)
            if len(examples) >= max_examples:
                break
        cleaned.loc[mask_series, col] = pd.NA
        audit[col] = {"count": flagged_count, "examples": examples}

    return cleaned, audit


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV file and validate it is non-empty.

    Raises SystemExit with a clear message on invalid input.
    """
    path = Path(path)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(path, na_values=EXTRA_NA_VALUES)
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(path, encoding="latin-1", na_values=EXTRA_NA_VALUES)
        except Exception as exc:
            print(f"Error: could not parse CSV: {exc}", file=sys.stderr)
            sys.exit(1)
    except Exception as exc:
        print(f"Error: could not parse CSV: {exc}", file=sys.stderr)
        sys.exit(1)

    if df.empty or len(df.columns) == 0:
        print("Error: CSV is empty or has no data rows.", file=sys.stderr)
        sys.exit(1)

    return df


def compute_summary(df: pd.DataFrame) -> dict:
    """Return shape, dtypes, and descriptive stats for numeric columns."""
    numeric_df = df.select_dtypes(include="number")
    desc = numeric_df.describe().to_dict() if not numeric_df.empty else {}

    return {
        "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        "dtypes": df.dtypes.astype(str).to_dict(),
        "numeric_summary": desc,
    }


def compute_schema(df: pd.DataFrame) -> list[dict]:
    """Return per-column metadata: name, dtype, unique count, sample values."""
    schema = []
    for col in df.columns:
        series = cast(pd.Series, df[col])
        sample = series.dropna().head(3).tolist()
        unique_count = int(pd.Index(series.dropna().unique()).size)
        missing_count = int(series.isna().to_numpy(dtype=bool).sum())
        schema.append(
            {
                "column": col,
                "dtype": str(series.dtype),
                "unique_count": unique_count,
                "missing_count": missing_count,
                "sample_values": sample,
            }
        )
    return schema


def compute_missingness(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with columns: column, missing_count, missing_pct."""
    cleaned, _ = coerce_suspicious_to_nan(df)
    missing_count = cleaned.isna().sum()
    missing_pct = (missing_count / len(cleaned) * 100).round(2)
    result = pd.DataFrame(
        {
            "column": cleaned.columns,
            "missing_count": missing_count.values,
            "missing_pct": missing_pct.values,
        }
    )
    return result.sort_values("missing_pct", ascending=False).reset_index(drop=True)
