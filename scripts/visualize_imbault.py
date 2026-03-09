from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- Make imports work even if you didn't `pip install -e .`
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from l2affect.utils.config import load_config, resolve  # noqa: E402

def annotate_top_words(ax, df, k=10, score_col="gap_mag"):
    top = df.sort_values(score_col, ascending=False).head(k)

    offsets = [
        (6, 6), (6, -6), (-6, 6), (-6, -6),
        (10, 0), (-10, 0), (0, 10), (0, -10),
        (12, 8), (-12, -8),
    ]
    for i, (_, r) in enumerate(top.iterrows()):
        dx, dy = offsets[i % len(offsets)]
        ax.annotate(
            str(r["word"]),
            (r["gap_valence"], r["gap_arousal"]),
            textcoords="offset points",
            xytext=(dx, dy),
            fontsize=8,
        )

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def main() -> None:
    ap = argparse.ArgumentParser(description="Visualize processed Imbault lexicon + gap data.")
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--gaps-file", default=None, help="Optional override path to gaps csv")
    ap.add_argument("--show", action="store_true", help="Show plots interactively")
    ap.add_argument("--bins", type=int, default=40, help="Histogram bins")
    args = ap.parse_args()

    cfg = load_config(args.config)

    processed_dir = resolve(cfg["paths"]["processed_dir"])
    fig_dir = resolve(cfg["paths"]["reports_figures_dir"])
    tbl_dir = resolve(cfg["paths"]["reports_tables_dir"])
    _ensure_dir(fig_dir)
    _ensure_dir(tbl_dir)

    # Default expected output from your cleaning step
    gaps_path = resolve(args.gaps_file) if args.gaps_file else (processed_dir / "imbault_gaps_va.csv")

    if not gaps_path.exists():
        raise FileNotFoundError(
            f"Could not find gaps file at: {gaps_path}\n"
            f"Run your cleaning script first to generate 'imbault_gaps_va.csv' into {processed_dir} "
            f"or pass --gaps-file path/to/file.csv"
        )

    gaps = pd.read_csv(gaps_path)

    required = {"word", "valence_l1", "arousal_l1", "valence_l2", "arousal_l2"}
    missing = required - set(gaps.columns)
    if missing:
        raise ValueError(f"Gaps file missing required columns: {missing}\nColumns found: {list(gaps.columns)}")

    # Ensure numeric
    for c in ["valence_l1", "arousal_l1", "valence_l2", "arousal_l2"]:
        gaps[c] = pd.to_numeric(gaps[c], errors="coerce")

    gaps = gaps.dropna(subset=["valence_l1", "arousal_l1", "valence_l2", "arousal_l2"]).copy()

    # Compute gaps if not present
    if "gap_valence" not in gaps.columns:
        gaps["gap_valence"] = gaps["valence_l2"] - gaps["valence_l1"]
    if "gap_arousal" not in gaps.columns:
        gaps["gap_arousal"] = gaps["arousal_l2"] - gaps["arousal_l1"]
    if "gap_mag" not in gaps.columns:
        gaps["gap_mag"] = np.sqrt(gaps["gap_valence"] ** 2 + gaps["gap_arousal"] ** 2)

    # ---- Summary stats (printed)
    print("\n=== Imbault gaps summary ===")
    print("Rows:", len(gaps))
    print("Valence gap (L2-L1): mean =", gaps["gap_valence"].mean(), "std =", gaps["gap_valence"].std())
    print("Arousal gap (L2-L1): mean =", gaps["gap_arousal"].mean(), "std =", gaps["gap_arousal"].std())
    print("Gap magnitude: mean =", gaps["gap_mag"].mean(), "std =", gaps["gap_mag"].std())

    # ---- Save separate "top gaps" tables (valence vs arousal)
    top_n = 50

    gaps["abs_gap_valence"] = gaps["gap_valence"].abs()
    gaps["abs_gap_arousal"] = gaps["gap_arousal"].abs()

    top_val = gaps.sort_values("abs_gap_valence", ascending=False).head(top_n).copy()
    top_aro = gaps.sort_values("abs_gap_arousal", ascending=False).head(top_n).copy()

    top_val_path = tbl_dir / "top_valence_gap_words.csv"
    top_aro_path = tbl_dir / "top_arousal_gap_words.csv"

    top_val.to_csv(top_val_path, index=False)
    top_aro.to_csv(top_aro_path, index=False)

    print("Saved:", top_val_path)
    print("Saved:", top_aro_path)

    # ---- Figure 1: Valence distributions (L1 vs L2)
    plt.figure()
    plt.hist(gaps["valence_l1"].values, bins=args.bins, alpha=0.6, label="L1 valence")
    plt.hist(gaps["valence_l2"].values, bins=args.bins, alpha=0.6, label="L2 valence")
    plt.title("Valence distributions (L1 vs L2)")
    plt.xlabel("Valence")
    plt.ylabel("Count")
    plt.legend()
    f1 = fig_dir / "valence_l1_vs_l2_hist.png"
    plt.tight_layout()
    plt.savefig(f1, dpi=200)
    print("Saved:", f1)

    # ---- Figure 2: Arousal distributions (L1 vs L2)
    plt.figure()
    plt.hist(gaps["arousal_l1"].values, bins=args.bins, alpha=0.6, label="L1 arousal")
    plt.hist(gaps["arousal_l2"].values, bins=args.bins, alpha=0.6, label="L2 arousal")
    plt.title("Arousal distributions (L1 vs L2)")
    plt.xlabel("Arousal")
    plt.ylabel("Count")
    plt.legend()
    f2 = fig_dir / "arousal_l1_vs_l2_hist.png"
    plt.tight_layout()
    plt.savefig(f2, dpi=200)
    print("Saved:", f2)

    # ---- Figure 3+4: Gap scatter (gap_valence vs gap_arousal), labeled by top valence + arousal gaps
    def make_scatter(df, label_score_col, title, out_name):
        fig, ax = plt.subplots()
        sc = ax.scatter(
            df["gap_valence"].values,
            df["gap_arousal"].values,
            c=df["gap_mag"].values,
            s=12,
            alpha=0.8,
        )
        ax.set_title(title)
        ax.set_xlabel("Valence gap (L2 - L1)")
        ax.set_ylabel("Arousal gap (L2 - L1)")
        ax.axhline(0, linewidth=1)
        ax.axvline(0, linewidth=1)
        fig.colorbar(sc, ax=ax, label="Gap magnitude")

        annotate_top_words(ax, df, k=10, score_col=label_score_col)

        out_path = fig_dir / out_name
        fig.tight_layout()
        fig.savefig(out_path, dpi=200)
        print("Saved:", out_path)

    # Scatter labeled by top 10 valence gap
    make_scatter(
        gaps,
        label_score_col="abs_gap_valence",
        title="L2–L1 affect gaps (top 10 |valence gap| labeled)",
        out_name="gap_scatter_top10_valence.png",
    )

    # Scatter labeled by top 10 arousal gap
    make_scatter(
        gaps,
        label_score_col="abs_gap_arousal",
        title="L2–L1 affect gaps (top 10 |arousal gap| labeled)",
        out_name="gap_scatter_top10_arousal.png",
    )

    # ---- Figure 5: Top valence-gap words (bar chart)
    top_n = 20
    top_val = gaps.sort_values("abs_gap_valence", ascending=False).head(top_n).copy()
    top_val = top_val.iloc[::-1]  # reverse for nicer horizontal bar order

    plt.figure(figsize=(10, 6))
    plt.barh(top_val["word"], top_val["gap_valence"])
    plt.title(f"Top {top_n} Valence Gap Words (L2 - L1)")
    plt.xlabel("Valence gap (L2 - L1)")
    plt.tight_layout()
    f5 = fig_dir / "top_valence_gap_bar.png"
    plt.savefig(f5, dpi=200)
    print("Saved:", f5)

    # ---- Figure 5: Top arousal-gap words (bar chart)
    top_aro = gaps.sort_values("abs_gap_arousal", ascending=False).head(top_n).copy()
    top_aro = top_aro.iloc[::-1]

    plt.figure(figsize=(10, 6))
    plt.barh(top_aro["word"], top_aro["gap_arousal"])
    plt.title(f"Top {top_n} Arousal Gap Words (L2 - L1)")
    plt.xlabel("Arousal gap (L2 - L1)")
    plt.tight_layout()
    f6 = fig_dir / "top_arousal_gap_bar.png"
    plt.savefig(f6, dpi=200)
    print("Saved:", f6)

if __name__ == "__main__":
    main()