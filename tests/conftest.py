"""Shared pytest fixtures."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """A well-formed CSV with numeric, categorical columns, and some nulls."""
    csv_path = tmp_path / "sample.csv"
    content = textwrap.dedent(
        """\
        id,age,salary,department,score
        1,25,50000,Engineering,88.5
        2,30,60000,Marketing,
        3,,75000,Engineering,92.0
        4,45,80000,,78.3
        5,28,55000,Marketing,85.0
        6,35,90000,Engineering,
        7,22,48000,HR,70.1
        8,40,70000,HR,
        9,33,65000,Marketing,81.0
        10,29,58000,Engineering,76.4
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def empty_csv(tmp_path: Path) -> Path:
    """A CSV file with a header but no data rows."""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("col1,col2,col3\n")
    return csv_path


@pytest.fixture()
def no_numeric_csv(tmp_path: Path) -> Path:
    """A CSV with only non-numeric columns."""
    csv_path = tmp_path / "no_numeric.csv"
    csv_path.write_text("name,city\nAlice,NYC\nBob,LA\n")
    return csv_path


@pytest.fixture()
def latin1_csv(tmp_path: Path) -> Path:
    """A CSV encoded in Latin-1 containing a £ sign (byte 0xa3)."""
    csv_path = tmp_path / "latin1.csv"
    csv_path.write_bytes("id,price\n1,£9.99\n2,£19.50\n".encode("latin-1"))
    return csv_path


@pytest.fixture()
def messy_csv(tmp_path: Path) -> Path:
    """CSV with real-world placeholder tokens that should be treated as missing."""
    csv_path = tmp_path / "messy.csv"
    content = textwrap.dedent(
        """\
        id,age,salary,department,score
        1,25,50000,??,88.5
        2,30,60000,Marketing,missing
        3,??,75000,Engineering,92.0
        4,45,80000,??missing,78.3
        5,28,55000,lost??,85.0
        6,35,90000,Engineering,????
        7,22,48000,HR,--
        8,40,70000,not available,91.0
        9,33,65000,Marketing,81.0
        10,29,58000,Engineering,76.4
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def false_positive_csv(tmp_path: Path) -> Path:
    """CSV with values that should not be mistaken for missing placeholders."""
    csv_path = tmp_path / "false_positive.csv"
    content = textwrap.dedent(
        """\
        id,description,category,status
        1,not missing,customer_missing_reason,lost_and_found
        2,something unknown here,missing_data_flag,found it
        3,value is present,reason_unknown_code,active
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def duplicates_csv(tmp_path: Path) -> Path:
    """CSV with exact duplicate rows for duplicate metrics."""
    csv_path = tmp_path / "duplicates.csv"
    content = textwrap.dedent(
        """\
        id,name,age
        1,Alice,30
        2,Bob,40
        2,Bob,40
        3,Carol,35
        3,Carol,35
        3,Carol,35
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def outliers_csv(tmp_path: Path) -> Path:
    """CSV with a clear numeric outlier and enough non-null values."""
    csv_path = tmp_path / "outliers.csv"
    content = textwrap.dedent(
        """\
        id,value,stable
        1,10,1
        2,11,1
        3,12,1
        4,13,1
        5,14,1
        6,15,1
        7,16,1
        8,17,1
        9,18,1
        10,19,1
        11,200,1
        12,18,1
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def constant_col_csv(tmp_path: Path) -> Path:
    """CSV with a constant-value column."""
    csv_path = tmp_path / "constant_col.csv"
    content = textwrap.dedent(
        """\
        id,constant,status
        1,same,active
        2,same,active
        3,same,inactive
        4,same,active
        5,same,inactive
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def high_cardinality_csv(tmp_path: Path) -> Path:
    """CSV with an identifier-like high-cardinality text column."""
    csv_path = tmp_path / "high_cardinality.csv"
    rows = ["id,session_key,segment"]
    for idx in range(1, 31):
        rows.append(f"{idx},sess_{idx:03d},{'A' if idx % 2 == 0 else 'B'}")
    csv_path.write_text("\n".join(rows) + "\n")
    return csv_path


@pytest.fixture()
def mixed_type_csv(tmp_path: Path) -> Path:
    """CSV with a text column containing mostly numeric values."""
    csv_path = tmp_path / "mixed_type.csv"
    content = textwrap.dedent(
        """\
        id,amount
        1,100
        2,200
        3,300
        4,oops
        5,500
        6,600
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def whitespace_csv(tmp_path: Path) -> Path:
    """CSV with leading/trailing whitespace in text values."""
    csv_path = tmp_path / "whitespace.csv"
    content = textwrap.dedent(
        """\
        id,city
        1,NYC
        2, LA
        3,SF 
        4,Chicago
        """
    )
    csv_path.write_text(content)
    return csv_path


@pytest.fixture()
def blank_colname_csv(tmp_path: Path) -> Path:
    """CSV with blank and duplicate header names in the raw header row."""
    csv_path = tmp_path / "blank_colname.csv"
    csv_path.write_text("id,,name,name\n1,10,A,a\n2,20,B,b\n")
    return csv_path
