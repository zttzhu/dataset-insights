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
