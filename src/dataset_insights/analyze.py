"""Core analysis functions: load, validate, and compute stats from a CSV."""

from __future__ import annotations

import csv
import re
import sys
import warnings
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pandas as pd


@dataclass
class QualityIssue:
    """A single data-quality finding produced by domain-agnostic checks."""

    rule: str
    severity: str
    column: str | None
    count: int
    pct: float
    examples: list[str] = field(default_factory=list)
    message: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "column": self.column,
            "count": self.count,
            "pct": round(self.pct, 2),
            "examples": self.examples,
            "message": self.message,
            "suggestion": self.suggestion,
        }


DUPLICATE_EXAMPLE_CAP = 5
OUTLIER_MIN_NONNULL = 10
HIGH_CARDINALITY_THRESHOLD = 0.95
HIGH_CARDINALITY_MIN_NONNULL = 20
CONSTANT_COLUMN_THRESHOLD = 1
MIXED_TYPE_NUMERIC_THRESHOLD = 0.50
PARSEABILITY_ACTIONABLE_LOW = 20.0
PARSEABILITY_ACTIONABLE_HIGH = 95.0


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


def _to_example_text(value: object) -> str:
    if value is None:
        return "None"
    return str(value)


def _to_serializable_scalar(value: object) -> object:
    try:
        if bool(pd.isna(value)):
            return None
    except Exception:
        pass

    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _read_raw_header(path: Path, encoding: str) -> list[str]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def inspect_header_issues(path: str | Path) -> list[QualityIssue]:
    """Read raw CSV headers and flag blank / duplicate names."""
    path_obj = Path(path)
    headers: list[str] = []
    for encoding in ("utf-8", "latin-1"):
        try:
            headers = _read_raw_header(path_obj, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except Exception:
            return []

    if not headers:
        return []

    issues: list[QualityIssue] = []
    cleaned = [h.strip() for h in headers]
    total_columns = len(cleaned)

    blank_positions = [i for i, name in enumerate(cleaned, start=1) if name == ""]
    if blank_positions:
        examples = [f"position {idx}" for idx in blank_positions[:DUPLICATE_EXAMPLE_CAP]]
        issues.append(
            QualityIssue(
                rule="blank_column_names",
                severity="critical",
                column=None,
                count=len(blank_positions),
                pct=round(len(blank_positions) / total_columns * 100, 2),
                examples=examples,
                message=(
                    f"Detected {len(blank_positions)} blank column name(s) in CSV header."
                ),
                suggestion="Rename blank headers to explicit, unique column names.",
            )
        )

    non_blank = [name for name in cleaned if name]
    counts = Counter(non_blank)
    duplicate_names = sorted(name for name, cnt in counts.items() if cnt > 1)
    duplicate_rows_excluding_first = sum(cnt - 1 for cnt in counts.values() if cnt > 1)
    if duplicate_names:
        issues.append(
            QualityIssue(
                rule="duplicate_column_names",
                severity="critical",
                column=None,
                count=duplicate_rows_excluding_first,
                pct=round(duplicate_rows_excluding_first / total_columns * 100, 2),
                examples=duplicate_names[:DUPLICATE_EXAMPLE_CAP],
                message=(
                    f"Detected {len(duplicate_names)} duplicate header name(s) in CSV header."
                ),
                suggestion="Rename duplicate headers to unique names before analysis.",
            )
        )

    return issues


def _coerce_issue(value: QualityIssue | dict[str, Any]) -> QualityIssue | None:
    if isinstance(value, QualityIssue):
        return value
    if not isinstance(value, dict):
        return None

    try:
        return QualityIssue(
            rule=str(value.get("rule", "")),
            severity=str(value.get("severity", "info")),
            column=cast(str | None, value.get("column")),
            count=int(value.get("count", 0)),
            pct=float(value.get("pct", 0.0)),
            examples=[str(v) for v in cast(list[Any], value.get("examples", []))],
            message=str(value.get("message", "")),
            suggestion=str(value.get("suggestion", "")),
        )
    except Exception:
        return None


def coerce_suspicious_to_nan(
    df: pd.DataFrame, max_examples: int = 5
) -> tuple[pd.DataFrame, dict[str, dict[str, int | list[str]]]]:
    """Coerce suspicious placeholder tokens to missing values.

    Returns:
        (cleaned_df, audit) where audit is:
        {column: {"count": <int>, "examples": [<unique_examples>]}}
    """
    cleaned = df.copy()
    cleaned.attrs = dict(df.attrs)
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

    df.attrs["header_issues"] = inspect_header_issues(path)
    return df


def compute_summary(df: pd.DataFrame) -> dict:
    """Return shape, dtypes, and descriptive stats for numeric columns."""
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.empty:
        desc: dict[str, dict[str, float | int | None]] = {}
    else:
        desc = cast(dict[str, dict[str, float | int | None]], numeric_df.describe().to_dict())
        skewness = numeric_df.skew(numeric_only=True)
        for col in numeric_df.columns:
            value = skewness.get(col, None)
            if value is None:
                desc.setdefault(col, {})["skewness"] = None
                continue

            try:
                value_float = float(value)
            except (TypeError, ValueError):
                desc.setdefault(col, {})["skewness"] = None
                continue

            if pd.isna(value_float):
                desc.setdefault(col, {})["skewness"] = None
            else:
                desc.setdefault(col, {})["skewness"] = value_float

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


def compute_duplicates(df: pd.DataFrame, max_examples: int = DUPLICATE_EXAMPLE_CAP) -> dict[str, Any]:
    """Compute duplicate-row metrics and return capped sample rows.

    Duplicate semantics are explicit:
    - duplicate_rows_excluding_first: rows beyond first occurrence in duplicate groups
    - duplicate_group_count: number of distinct row groups with count > 1
    - duplicate_row_pct: duplicate_rows_excluding_first / total_rows * 100
    """
    total_rows = int(len(df))
    if total_rows == 0:
        return {
            "total_rows": 0,
            "duplicate_rows_excluding_first": 0,
            "duplicate_group_count": 0,
            "duplicate_row_pct": 0.0,
            "example_limit": max_examples,
            "example_rows": [],
            "omitted_count": 0,
            "truncated": False,
        }

    duplicate_mask = df.duplicated(keep="first")
    duplicate_rows_excluding_first = int(duplicate_mask.sum())

    value_counts = df.value_counts(dropna=False)
    duplicate_group_count = int((value_counts > 1).sum())
    duplicate_row_pct = round(duplicate_rows_excluding_first / total_rows * 100, 2)

    example_rows: list[dict[str, object]] = []
    if duplicate_rows_excluding_first > 0:
        sample = df.loc[duplicate_mask].head(max_examples)
        for _, row in sample.iterrows():
            row_dict = {
                str(col): _to_serializable_scalar(val)
                for col, val in row.to_dict().items()
            }
            example_rows.append(row_dict)

    omitted_count = max(duplicate_rows_excluding_first - len(example_rows), 0)
    return {
        "total_rows": total_rows,
        "duplicate_rows_excluding_first": duplicate_rows_excluding_first,
        "duplicate_group_count": duplicate_group_count,
        "duplicate_row_pct": duplicate_row_pct,
        "example_limit": max_examples,
        "example_rows": example_rows,
        "omitted_count": omitted_count,
        "truncated": omitted_count > 0,
    }


def compute_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Compute IQR-based outlier counts per numeric column.

    Columns with too few non-null values are skipped.
    """
    columns = [
        "column",
        "non_null_count",
        "q1",
        "q3",
        "iqr",
        "lower_bound",
        "upper_bound",
        "outlier_count",
        "outlier_pct",
    ]

    numeric_df = df.select_dtypes(include="number")
    rows: list[dict[str, Any]] = []
    for col in numeric_df.columns:
        series = cast(pd.Series, numeric_df[col]).dropna()
        non_null = int(len(series))
        if non_null < OUTLIER_MIN_NONNULL:
            continue

        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        mask = (series < lower_bound) | (series > upper_bound)
        outlier_count = int(mask.sum())
        outlier_pct = round(outlier_count / non_null * 100, 2)

        rows.append(
            {
                "column": str(col),
                "non_null_count": non_null,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "outlier_count": outlier_count,
                "outlier_pct": outlier_pct,
            }
        )

    if not rows:
        return pd.DataFrame(columns=columns)

    result = pd.DataFrame(rows, columns=columns)
    return result.sort_values(["outlier_pct", "outlier_count"], ascending=False).reset_index(
        drop=True
    )


def compute_parseability(df: pd.DataFrame) -> pd.DataFrame:
    """Compute numeric/datetime parseability rates for text columns."""
    columns = [
        "column",
        "non_null_count",
        "non_empty_count",
        "numeric_parseable_count",
        "numeric_parse_pct",
        "datetime_parseable_count",
        "datetime_parse_pct",
    ]
    rows: list[dict[str, Any]] = []

    text_columns = df.select_dtypes(include=["object", "string"]).columns
    for col in text_columns:
        series = cast(pd.Series, df[col]).dropna().astype(str)
        non_null_count = int(len(series))
        stripped = series.str.strip()
        non_empty_mask = stripped.ne("")
        candidate = stripped.loc[non_empty_mask]
        non_empty_count = int(len(candidate))

        if non_empty_count == 0:
            numeric_count = 0
            datetime_count = 0
        else:
            numeric_values = pd.to_numeric(candidate, errors="coerce")
            numeric_count = int(sum(bool(pd.notna(v)) for v in pd.Series(numeric_values).tolist()))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                datetime_values = pd.to_datetime(candidate, errors="coerce")
            datetime_count = int(
                sum(bool(pd.notna(v)) for v in pd.Series(datetime_values).tolist())
            )

        numeric_pct = round((numeric_count / non_empty_count * 100), 2) if non_empty_count else 0.0
        datetime_pct = (
            round((datetime_count / non_empty_count * 100), 2) if non_empty_count else 0.0
        )

        rows.append(
            {
                "column": str(col),
                "non_null_count": non_null_count,
                "non_empty_count": non_empty_count,
                "numeric_parseable_count": numeric_count,
                "numeric_parse_pct": numeric_pct,
                "datetime_parseable_count": datetime_count,
                "datetime_parse_pct": datetime_pct,
            }
        )

    return pd.DataFrame(rows, columns=columns)


def detect_column_warnings(
    df: pd.DataFrame,
    actionable_low: float = PARSEABILITY_ACTIONABLE_LOW,
    actionable_high: float = PARSEABILITY_ACTIONABLE_HIGH,
) -> tuple[list[QualityIssue], pd.DataFrame]:
    """Detect broad, domain-agnostic quality issues.

    Parseability rates are always returned as metrics, while warnings are emitted
    only when they are actionable.
    """
    issues: list[QualityIssue] = []

    header_issues_raw = cast(list[Any], df.attrs.get("header_issues", []))
    for raw_issue in header_issues_raw:
        issue = _coerce_issue(raw_issue)
        if issue is not None:
            issues.append(issue)

    for col in df.columns:
        series = cast(pd.Series, df[col])
        non_null = int(series.notna().sum())
        if non_null == 0:
            continue

        is_text = pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)

        non_null_series = series.dropna()
        unique_count = int(non_null_series.nunique(dropna=True))
        unique_ratio = unique_count / non_null

        if unique_count <= CONSTANT_COLUMN_THRESHOLD:
            examples = [_to_example_text(v) for v in non_null_series.head(3).tolist()]
            issues.append(
                QualityIssue(
                    rule="constant_column",
                    severity="warn",
                    column=str(col),
                    count=unique_count,
                    pct=round(unique_ratio * 100, 2),
                    examples=examples,
                    message=f"Column '{col}' has a single repeated value.",
                    suggestion="Drop it or verify whether upstream ingestion collapsed variation.",
                )
            )

        if (
            is_text
            and non_null >= HIGH_CARDINALITY_MIN_NONNULL
            and unique_ratio >= HIGH_CARDINALITY_THRESHOLD
        ):
            issues.append(
                QualityIssue(
                    rule="high_cardinality_column",
                    severity="info",
                    column=str(col),
                    count=unique_count,
                    pct=round(unique_ratio * 100, 2),
                    examples=[_to_example_text(v) for v in non_null_series.head(3).tolist()],
                    message=(
                        f"Column '{col}' has high cardinality ({unique_count}/{non_null} unique)."
                    ),
                    suggestion="Treat as identifier/free text or encode with care for modeling.",
                )
            )

        if is_text:
            text_series = non_null_series.astype(str)
            stripped = text_series.str.strip()
            whitespace_mask = text_series.ne(stripped)
            whitespace_count = int(whitespace_mask.sum())
            if whitespace_count > 0:
                examples = []
                seen_examples: set[str] = set()
                for value in text_series.loc[whitespace_mask].tolist():
                    if value in seen_examples:
                        continue
                    seen_examples.add(value)
                    examples.append(value)
                    if len(examples) >= 3:
                        break
                issues.append(
                    QualityIssue(
                        rule="leading_trailing_whitespace",
                        severity="warn",
                        column=str(col),
                        count=whitespace_count,
                        pct=round(whitespace_count / non_null * 100, 2),
                        examples=examples,
                        message=(
                            f"Column '{col}' contains leading/trailing whitespace in text values."
                        ),
                        suggestion="Trim whitespace before grouping, joining, or deduplicating.",
                    )
                )

    parseability = compute_parseability(df)
    for row in parseability.to_dict(orient="records"):
        column = str(row["column"])
        non_empty_count = int(row["non_empty_count"])
        numeric_count = int(row["numeric_parseable_count"])
        numeric_pct = float(row["numeric_parse_pct"])
        datetime_count = int(row["datetime_parseable_count"])
        datetime_pct = float(row["datetime_parse_pct"])

        if non_empty_count == 0:
            continue

        partial_numeric = 0 < numeric_count < non_empty_count
        partial_datetime = 0 < datetime_count < non_empty_count

        if partial_numeric and numeric_pct >= MIXED_TYPE_NUMERIC_THRESHOLD * 100:
            issues.append(
                QualityIssue(
                    rule="mixed_type_numeric_text",
                    severity="warn",
                    column=column,
                    count=numeric_count,
                    pct=numeric_pct,
                    examples=[],
                    message=(
                        f"Column '{column}' is text but {numeric_pct:.2f}% of non-empty values are numeric-parseable."
                    ),
                    suggestion="Normalize mixed tokens and cast to numeric if semantically appropriate.",
                )
            )
            continue

        if numeric_count == non_empty_count and non_empty_count > 0:
            issues.append(
                QualityIssue(
                    rule="convertible_numeric_text",
                    severity="info",
                    column=column,
                    count=numeric_count,
                    pct=numeric_pct,
                    examples=[],
                    message=(
                        f"Column '{column}' is text but fully numeric-parseable ({numeric_pct:.2f}%)."
                    ),
                    suggestion="Consider casting this column to numeric dtype.",
                )
            )
            continue

        numeric_actionable = partial_numeric and actionable_low <= numeric_pct <= actionable_high
        datetime_actionable = (
            partial_datetime and actionable_low <= datetime_pct <= actionable_high
        )
        if numeric_actionable or datetime_actionable:
            parts = []
            if numeric_actionable:
                parts.append(f"numeric parseability {numeric_pct:.2f}%")
            if datetime_actionable:
                parts.append(f"datetime parseability {datetime_pct:.2f}%")

            issues.append(
                QualityIssue(
                    rule="partial_parseability",
                    severity="info",
                    column=column,
                    count=non_empty_count,
                    pct=max(numeric_pct, datetime_pct),
                    examples=[],
                    message=(
                        f"Column '{column}' has partial parseability ({'; '.join(parts)})."
                    ),
                    suggestion=(
                        "Inspect token patterns and standardize formats before converting dtype."
                    ),
                )
            )

    return issues, parseability


def summarize_quality_issues(issues: list[QualityIssue]) -> dict[str, int]:
    """Return counts by severity for quick CLI summaries."""
    counts = {"critical": 0, "warn": 0, "info": 0}
    for issue in issues:
        if issue.severity in counts:
            counts[issue.severity] += 1
    return counts
