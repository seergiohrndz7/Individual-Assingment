"""
plot_benchmarks.py
Generates comparative figures (grouped bar charts + improved boxplots) and
a LaTeX snippet that includes them.

Input CSV schema:
  language,matrix_size,run_index,elapsed_sec,memory_used_mb,timestamp_iso

Usage (from repo root):
  python scripts/plot_benchmarks.py
  python scripts/plot_benchmarks.py --csv data/results.csv --out paper/figures --show

Requirements:
  pip install pandas matplotlib
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# -------------------- IO & summary -------------------- #

def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"[ERROR] CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    expected = {"language", "matrix_size", "run_index", "elapsed_sec", "memory_used_mb", "timestamp_iso"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"[ERROR] Missing columns in CSV: {sorted(missing)}")

    df["language"] = df["language"].astype(str)
    df["matrix_size"] = df["matrix_size"].astype(int)
    df["run_index"] = df["run_index"].astype(int)
    df["elapsed_sec"] = df["elapsed_sec"].astype(float)
    df["memory_used_mb"] = df["memory_used_mb"].astype(float)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["language", "matrix_size"])
          .agg(
              runs=("run_index", "count"),
              avg_time_s=("elapsed_sec", "mean"),
              std_time_s=("elapsed_sec", "std"),
              avg_mem_mb=("memory_used_mb", "mean"),
              std_mem_mb=("memory_used_mb", "std"),
          )
          .reset_index()
          .sort_values(["language", "matrix_size"])
    )


# -------------------- helper: color cycle -------------------- #

def color_cycle(n: int):
    # stable palette from tab10 for consistency across figs
    cmap = plt.cm.get_cmap("tab10")
    return [cmap(i % 10) for i in range(n)]


# -------------------- classic average/ speedup (optional) -------------------- #

def fig_avg_time(summary: pd.DataFrame, outdir: Path, show: bool = False) -> Path:
    p = outdir / "avg_time_by_language.png"
    plt.figure()
    for lang, g in summary.groupby("language"):
        g = g.sort_values("matrix_size")
        plt.plot(g["matrix_size"], g["avg_time_s"], marker="o", label=lang)
    plt.xlabel("Matrix size (n)")
    plt.ylabel("Average elapsed time (s)")
    plt.title("Average Time vs Size")
    plt.grid(True, axis="y")
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, bbox_inches="tight")
    if show: plt.show()
    plt.close()
    return p


def fig_avg_mem(summary: pd.DataFrame, outdir: Path, show: bool = False) -> Path:
    p = outdir / "avg_memory_by_language.png"
    plt.figure()
    for lang, g in summary.groupby("language"):
        g = g.sort_values("matrix_size")
        plt.plot(g["matrix_size"], g["avg_mem_mb"], marker="o", label=lang)
    plt.xlabel("Matrix size (n)")
    plt.ylabel("Average memory used (MB)")
    plt.title("Average Memory vs Size")
    plt.grid(True, axis="y")
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, bbox_inches="tight")
    if show: plt.show()
    plt.close()
    return p


def fig_speedup_vs_python(summary: pd.DataFrame, outdir: Path, show: bool = False):
    if "Python" not in summary["language"].unique():
        return None, None
    base = summary[summary["language"] == "Python"][["matrix_size", "avg_time_s"]].rename(columns={"avg_time_s": "python_avg"})
    merged = summary.merge(base, on="matrix_size", how="left")
    merged["speedup_vs_python"] = merged["python_avg"] / merged["avg_time_s"]
    speedup = merged[merged["language"] != "Python"].copy()

    # table next to summary
    tbl_path = outdir.parent / "speedup_vs_python.csv"
    speedup[["language", "matrix_size", "speedup_vs_python"]].to_csv(tbl_path, index=False)

    p = outdir / "speedup_vs_python.png"
    plt.figure()
    for lang, g in speedup.groupby("language"):
        g = g.sort_values("matrix_size")
        plt.plot(g["matrix_size"], g["speedup_vs_python"], marker="o", label=lang)
    plt.xlabel("Matrix size (n)")
    plt.ylabel("Speedup vs Python (×)")
    plt.title("Speedup Relative to Python")
    plt.grid(True, axis="y")
    plt.legend()
    plt.tight_layout()
    plt.savefig(p, bbox_inches="tight")
    if show: plt.show()
    plt.close()
    return p, tbl_path


# -------------------- NEW: Grouped bar charts (with error bars) -------------------- #

def grouped_bar(summary: pd.DataFrame, value_col: str, err_col: str, ylabel: str, filename: str,
                outdir: Path, show: bool = False) -> Path:
    """
    One bar group per matrix_size; bars inside group per language.
    Error bars = std (if available).
    """
    p = outdir / filename
    langs = sorted(summary["language"].unique().tolist())
    sizes = sorted(summary["matrix_size"].unique().tolist())
    colors = color_cycle(len(langs))

    # Arrange data by size for consistent group ordering
    width = 0.8 / max(1, len(langs))  # total width <= 0.8
    x = np.arange(len(sizes))  # group centers

    plt.figure(figsize=(max(6, len(sizes)*0.9), 4.8))
    for i, lg in enumerate(langs):
        g = summary[summary["language"] == lg].set_index("matrix_size").reindex(sizes)
        vals = g[value_col].to_numpy()
        errs = g[err_col].to_numpy() if err_col in g else np.zeros_like(vals)
        plt.bar(x + i*width - (len(langs)-1)*width/2, vals, width, yerr=errs, capsize=3,
                label=lg, color=colors[i], edgecolor="black")

    plt.xticks(x, [str(s) for s in sizes])
    plt.xlabel("Matrix size (n)")
    plt.ylabel(ylabel)
    plt.title(f"{ylabel} — Grouped by Language")
    plt.grid(True, axis="y", alpha=0.35)
    plt.legend(ncol=min(4, len(langs)))
    plt.tight_layout()
    plt.savefig(p, bbox_inches="tight")
    if show: plt.show()
    plt.close()
    return p


# -------------------- NEW: Boxplots (compact grid across sizes) -------------------- #

def box_grid(df: pd.DataFrame, metric_col: str, ylabel: str, filename: str,
            outdir: Path, show: bool = False) -> Path:
    """
    Build a grid of boxplots: one subplot per matrix_size.
    Each subplot shows a boxplot by language for the given metric.
    """
    p = outdir / filename
    sizes = sorted(df["matrix_size"].unique().tolist())
    langs = sorted(df["language"].unique().tolist())
    n = len(sizes)
    ncols = 3 if n >= 3 else n
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4*ncols, 3.2*nrows), squeeze=False)
    colors = color_cycle(len(langs))

    for idx, size in enumerate(sizes):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        sub = df[df["matrix_size"] == size]
        data = [sub[sub["language"] == lg][metric_col].to_numpy() for lg in langs]
        bp = ax.boxplot(data, labels=langs, patch_artist=True, showfliers=True)
        # style boxes
        for patch, col in zip(bp['boxes'], colors):
            patch.set(facecolor=col, alpha=0.6, edgecolor="black")
        for median in bp['medians']:
            median.set(color='black', linewidth=1.3)

        ax.set_title(f"n={size}")
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.35)
        # tilt labels if many languages
        if len(langs) > 4:
            for tick in ax.get_xticklabels():
                tick.set_rotation(15)

    # Hide any empty subplots
    for j in range(n, nrows*ncols):
        r, c = divmod(j, ncols)
        axes[r][c].axis("off")

    fig.suptitle(f"{ylabel} — Boxplots by Language and Size", y=0.98)
    fig.tight_layout()
    plt.savefig(p, bbox_inches="tight")
    if show: plt.show()
    plt.close()
    return p


# -------------------- LaTeX snippet -------------------- #

def write_bars_boxplots_snippet(outdir: Path) -> Path:
    """
    Writes paper/figures_bars_boxplots.tex with four \figure blocks:
    - bar_time_grouped.png
    - bar_mem_grouped.png
    - box_time_all_sizes.png
    - box_mem_all_sizes.png
    """
    tex = []
    tex.append("% Auto-generated by plot_benchmarks.py")
    tex.append("% Grouped bar charts and boxplot grids")

    def figline(img, caption, label):
        return (
            "\\begin{figure}[H]\n"
            "  \\centering\n"
            f"  \\includegraphics[width=.90\\linewidth]{{{img}}}\n"
            f"  \\caption{{{caption}}}\n"
            f"  \\label{{{label}}}\n"
            "\\end{figure}\n"
        )

    tex.append(figline("bar_time_grouped.png",
                       "Average elapsed time with standard-deviation error bars (grouped by language and matrix size).",
                       "fig:bar-time"))
    tex.append(figline("bar_mem_grouped.png",
                       "Average memory usage with standard-deviation error bars (grouped by language and matrix size).",
                       "fig:bar-mem"))
    tex.append(figline("box_time_all_sizes.png",
                       "Elapsed time distributions (boxplots) by language across all matrix sizes.",
                       "fig:box-time"))
    tex.append(figline("box_mem_all_sizes.png",
                       "Memory usage distributions (boxplots) by language across all matrix sizes.",
                       "fig:box-mem"))

    snippet = outdir.parent / "figures_bars_boxplots.tex"
    snippet.write_text("\n".join(tex), encoding="utf-8")
    return snippet


# -------------------- main -------------------- #

def main():
    ap = argparse.ArgumentParser(description="Generate grouped bar charts and boxplots + LaTeX snippet from results.csv")
    ap.add_argument("--csv", type=Path, default=Path("data/results.csv"))
    ap.add_argument("--out", type=Path, default=Path("paper/figures"))
    ap.add_argument("--summary-out", type=Path, default=Path("paper/summary_stats.csv"))
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    df = load_data(args.csv)
    args.out.mkdir(parents=True, exist_ok=True)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)

    # Summary and save
    summary = summarize(df)
    summary.to_csv(args.summary_out, index=False)

    # Optional averages/speedup (kept for completeness)
    fig_avg_time(summary, args.out, args.show)
    fig_avg_mem(summary, args.out, args.show)
    fig_speedup_vs_python(summary, args.out, args.show)

    # === NEW required plots ===
    # 1) grouped bar — time & memory with error bars
    grouped_bar(summary, "avg_time_s", "std_time_s",
                ylabel="Average elapsed time (s)",
                filename="bar_time_grouped.png", outdir=args.out, show=args.show)

    grouped_bar(summary, "avg_mem_mb", "std_mem_mb",
                ylabel="Average memory used (MB)",
                filename="bar_mem_grouped.png", outdir=args.out, show=args.show)

    # 2) boxplot grids — time & memory across sizes
    box_grid(df, "elapsed_sec", "Elapsed time (s)",
             filename="box_time_all_sizes.png", outdir=args.out, show=args.show)

    box_grid(df, "memory_used_mb", "Memory used (MB)",
             filename="box_mem_all_sizes.png", outdir=args.out, show=args.show)

    # Write LaTeX snippet that includes the four figs above
    snippet = write_bars_boxplots_snippet(args.out)

    print("\n=== DONE ===")
    print(f"Summary CSV: {args.summary_out.resolve()}")
    print(f"LaTeX snippet written to: {snippet.resolve()}")
    print(f"Figures dir: {args.out.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(1)
