"""Plot generators: histogram, correlation heatmap, missingness bar, box plot."""

from __future__ import annotations

from numbers import Real
from pathlib import Path
from typing import cast

import matplotlib
matplotlib.use("Agg")  # headless rendering — must be set before importing pyplot
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


_MAX_HISTOGRAM_COLS = 6  # hard cap on subplots
_MAX_HEATMAP_COLS = 20   # cap columns shown in correlation heatmap
_MAX_BOXPLOT_COLS = 6
_MAX_BOXPLOT_ROWS = 50_000


def _ensure_plots_dir(outdir: Path) -> Path:
    plots_dir = outdir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)
    return plots_dir


def plot_distribution_histogram(df: pd.DataFrame, outdir: Path) -> Path | None:
    """Histograms for up to 6 numeric columns. Returns None if no numeric cols."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    cols = numeric_cols[:_MAX_HISTOGRAM_COLS]
    n = len(cols)
    ncols = min(n, 3)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(5 * ncols, 4 * nrows), squeeze=False)
    fig.suptitle("Distribution of Numeric Columns", fontsize=14, y=1.02)

    for idx, col in enumerate(cols):
        ax = axes[idx // ncols][idx % ncols]
        df[col].dropna().plot(kind="hist", bins=30, ax=ax, color="steelblue", edgecolor="white")
        ax.set_title(col, fontsize=10)
        ax.set_xlabel("")
        ax.set_ylabel("Count")

    # Hide unused subplots
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].set_visible(False)

    plt.tight_layout()
    out_path = _ensure_plots_dir(outdir) / "distribution_histogram.png"
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_correlation_heatmap(df: pd.DataFrame, outdir: Path) -> Path | None:
    """Correlation heatmap for numeric columns. Returns None if fewer than 2 numeric cols.

    When more than _MAX_HEATMAP_COLS numeric columns are present the plot is
    limited to the first 20 columns for readability.  The full correlation
    matrix is always available via ``write_correlation_csv`` in reports.py.
    """
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return None

    n_total = numeric_df.shape[1]
    truncated = n_total > _MAX_HEATMAP_COLS
    if truncated:
        numeric_df = numeric_df.iloc[:, :_MAX_HEATMAP_COLS]

    corr = numeric_df.corr()
    n = len(corr)
    use_annot = n <= 15
    fig, ax = plt.subplots(figsize=(max(6, n * 0.8), max(5, n * 0.7)))

    heatmap_kwargs: dict = dict(
        cmap="coolwarm",
        center=0,
        linewidths=0.5,
        ax=ax,
    )
    if use_annot:
        heatmap_kwargs.update(annot=True, fmt=".2f", annot_kws={"size": 8})

    sns.heatmap(corr, **heatmap_kwargs)

    title = "Correlation Heatmap"
    if truncated:
        title += f"  (showing {_MAX_HEATMAP_COLS} of {n_total} numeric columns)"
    ax.set_title(title, fontsize=13)
    ax.tick_params(axis="x", rotation=45)
    ax.tick_params(axis="y", rotation=0)
    plt.tight_layout()
    out_path = _ensure_plots_dir(outdir) / "correlation_heatmap.png"
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_missingness_bar(df: pd.DataFrame, outdir: Path) -> Path:
    """Bar chart of missing % per column."""
    missing_pct = (df.isna().sum() / len(df) * 100).sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(max(8, len(missing_pct) * 0.5), 5))
    colors = ["#e74c3c" if v > 0 else "#95a5a6" for v in missing_pct.values]
    ax.bar(missing_pct.index, missing_pct.values, color=colors)
    ax.set_title("Missing Data (%) per Column", fontsize=13)
    ax.set_ylabel("Missing %")
    ax.set_xlabel("Column")
    ax.tick_params(axis="x", rotation=45)
    ax.axhline(y=0, color="black", linewidth=0.8)
    plt.tight_layout()

    out_path = _ensure_plots_dir(outdir) / "missingness_bar.png"
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_box_plots(
    df: pd.DataFrame,
    outdir: Path,
    outliers: pd.DataFrame | None = None,
) -> Path | None:
    """Box plot for numeric columns, capped for readability and speed."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return None

    if outliers is not None and not outliers.empty and {"column", "outlier_pct"}.issubset(outliers.columns):
        outlier_rate: dict[str, float] = {}
        column_values = outliers["column"].tolist()
        outlier_pct_values = outliers["outlier_pct"].tolist()
        for key_raw, raw_rate in zip(column_values, outlier_pct_values):
            key = str(key_raw)
            if isinstance(raw_rate, Real):
                outlier_rate[key] = float(raw_rate)
            else:
                outlier_rate[key] = 0.0
        ordered_cols = sorted(numeric_cols, key=lambda c: outlier_rate.get(c, 0.0), reverse=True)
    else:
        ordered_cols = numeric_cols

    cols = ordered_cols[:_MAX_BOXPLOT_COLS]
    plot_df = cast(pd.DataFrame, df.loc[:, cols])

    sampled = False
    if len(plot_df) > _MAX_BOXPLOT_ROWS:
        plot_df = cast(pd.DataFrame, plot_df.sample(n=_MAX_BOXPLOT_ROWS, random_state=42))
        sampled = True

    fig, ax = plt.subplots(figsize=(max(8, len(cols) * 1.2), 5))
    sns.boxplot(data=cast(pd.DataFrame, plot_df), ax=ax)
    title = "Box Plot of Numeric Columns"
    if sampled:
        title += f" (sampled {_MAX_BOXPLOT_ROWS:,} rows)"
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Column")
    ax.set_ylabel("Value")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()

    out_path = _ensure_plots_dir(outdir) / "box_plot.png"
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return out_path
