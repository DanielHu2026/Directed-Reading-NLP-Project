from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from l2affect.utils.config import load_config, resolve  # noqa: E402


BOT_PATTERNS = [
    r"the character limit for a tweet is\s*280",
    r"hello writestreakians",
    r"remember, if you didn[’']t write yesterday, your streak number is 1",
    r"if you want to make a comment, write below",
    r"english natives, please help us correct posts",
    r"subjects of the day",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--infile", default=None, help="Override input CSV path")
    ap.add_argument("--outfile", default=None, help="Override cleaned output CSV path")
    args = ap.parse_args()

    cfg = load_config(args.config)
    proc_dir = resolve(cfg["paths"]["processed_dir"])

    in_path = resolve(args.infile) if args.infile else (proc_dir / "writestreak_posts_base.csv")
    out_path = resolve(args.outfile) if args.outfile else (proc_dir / "writestreak_posts_base_clean.csv")
    removed_path = proc_dir / "writestreak_posts_removed_botposts.csv"

    df = pd.read_csv(in_path)
    text = df["selftext"].fillna("").astype(str).str.lower()

    mask = pd.Series(False, index=df.index)
    for p in BOT_PATTERNS:
        mask = mask | text.str.contains(p, regex=True)

    removed = df[mask].copy()
    clean = df[~mask].copy()

    clean.to_csv(out_path, index=False)
    removed.to_csv(removed_path, index=False)

    print(f"Input rows: {len(df)}")
    print(f"Removed bot/meta posts: {len(removed)}")
    print(f"Kept rows: {len(clean)}")
    print("Wrote:", out_path)
    print("Wrote:", removed_path)


if __name__ == "__main__":
    main()