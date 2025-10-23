"""
plot_benchmarks.py
Reads a results.csv with columns:
  language,matrix_size,run_index,elapsed_sec,memory_used_mb,timestamp_iso
and generates comparative figures + summary CSVs.

Usage (desde la raíz del repo):
  python scripts/plot_benchmarks.py
  python scripts/plot_benchmarks.py --csv data/results.csv --out paper/figures
  python scripts/plot_benchmarks.py --show   # para abrir ventanas interactivas

Requisitos:
  pip install pandas matplotlib
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def load_data(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"[ERROR] CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    expected = {"language", "matrix_size", "run_index", "elapsed_sec", "memory_used_mb", "timestamp_iso"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"[ERROR] Missing columns in CSV: {sorted(missing)}")

    # types
    df["language"] = df["language"].astype(str)
    df["matrix_size"] = df["matrix_size"].astype(int)
    df["run_index"] = df["run_index"].astype(int)
    df["elapsed_sec"] = df["elapsed_sec"].astype(float)
    df["memory_used_mb"] = df["memory_used_mb"].astype(float)
    return df


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
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
    return summary


def fig_avg_time(summary: pd.DataFrame, outdir: Path, show: bool = False) -> Path:
    p = outdir / "avg_time_by_language.png"
    plt.figure()
    for lang, g in summary.groupby("language"):
        g = g.sort_values("matrix_size")
        plt.plot(g["matrix_size"], g["avg_time_s"], marker="o", label=lang)
    plt.xlabel("Matrix size (n)")
    plt.ylabel("Average elapsed time (s)")
    plt.title("Matrix Multiplication: Average Time vs Size")
    plt.grid(True)
    plt.legend()
    plt.savefig(p, bbox_inches="tight")
    if show:
        plt.show()
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
    plt.title("Matrix Multiplication: Average Memory vs Size")
    plt.grid(True)
    plt.legend()
    plt.savefig(p, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()
    return p


def fig_speedup_vs_python(summary: pd.DataFrame, outdir: Path, show: bool = False) -> Path | None:
    if "Python" not in summary["language"].unique():
        return None
    base = (
        summary[summary["language"] == "Python"][["matrix_size", "avg_time_s"]]
        .rename(columns={"avg_time_s": "python_avg"})
    )
    merged = summary.merge(base, on="matrix_size", how="left")
    merged["speedup_vs_python"] = merged["python_avg"] / merged["avg_time_s"]
    speedup = merged[merged["language"] != "Python"].copy()

    # saves table
    tbl_path = outdir / "speedup_vs_python.csv"
    speedup[["language", "matrix_size", "speedup_vs_python"]].to_csv(tbl_path, index=False)

    # figure
    p = outdir / "speedup_vs_python.png"
    plt.figure()
    for lang, g in speedup.groupby("language"):
        g = g.sort_values("matrix_size")
        plt.plot(g["matrix_size"], g["speedup_vs_python"], marker="o", label=lang)
    plt.xlabel("Matrix size (n)")
    plt.ylabel("Speedup vs Python (×)")
    plt.title("Speedup Relative to Python")
    plt.grid(True)
    plt.legend()
    plt.savefig(p, bbox_inches="tight")
    if show:
        plt.show()
    plt.close()
    return p


def fig_boxplots(df: pd.DataFrame, outdir: Path, show: bool = False) -> list[Path]:
    paths: list[Path] = []
    sizes = sorted(df["matrix_size"].unique().tolist())
    for n in sizes:
        sub = df[df["matrix_size"] == n]
        if sub.empty:
            continue
        langs = sorted(sub["language"].unique().tolist())

        # time
        p_time = outdir / f"box_time_n{n}.png"
        plt.figure()
        data_t = [sub[sub["language"] == lg]["elapsed_sec"].values for lg in langs]
        plt.boxplot(data_t, labels=langs, showfliers=True)
        plt.ylabel("Elapsed time (s)")
        plt.title(f"Elapsed Time Distribution by Language (n={n})")
        plt.grid(True, axis="y")
        plt.savefig(p_time, bbox_inches="tight")
        if show:
            plt.show()
        plt.close()
        paths.append(p_time)

        # memory
        p_mem = outdir / f"box_mem_n{n}.png"
        plt.figure()
        data_m = [sub[sub["language"] == lg]["memory_used_mb"].values for lg in langs]
        plt.boxplot(data_m, labels=langs, showfliers=True)
        plt.ylabel("Memory used (MB)")
        plt.title(f"Memory Distribution by Language (n={n})")
        plt.grid(True, axis="y")
        plt.savefig(p_mem, bbox_inches="tight")
        if show:
            plt.show()
        plt.close()
        paths.append(p_mem)
    return paths


def main():
    ap = argparse.ArgumentParser(description="Generate comparative plots from results.csv")
    ap.add_argument("--csv", type=Path, default=Path("data/results.csv"),
                    help="Path to results.csv (default: data/results.csv)")
    ap.add_argument("--out", type=Path, default=Path("paper/figures"),
                    help="Output directory for figures (default: paper/figures)")
    ap.add_argument("--summary-out", type=Path, default=Path("paper/summary_stats.csv"),
                    help="Path to save summary CSV (default: paper/summary_stats.csv)")
    ap.add_argument("--show", action="store_true", help="Show interactive windows (matplotlib)")
    args = ap.parse_args()

    # Load
    df = load_data(args.csv)

    # Ensure dirs
    args.out.mkdir(parents=True, exist_ok=True)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)

    # Summaries
    summary = summarize(df)
    summary.to_csv(args.summary_out, index=False)

    # Figures
    paths = []
    paths.append(fig_avg_time(summary, args.out, args.show))
    paths.append(fig_avg_mem(summary, args.out, args.show))
    sp = fig_speedup_vs_python(summary, args.out, args.show)
    if sp is not None:
        paths.append(sp)
    paths.extend(fig_boxplots(df, args.out, args.show))

    print("\n=== Done ===")
    print(f"Summary CSV: {args.summary_out.resolve()}")
    print("Figures:")
    for p in paths:
        print(" -", Path(p).resolve())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", file=sys.stderr)
        sys.exit(1)
