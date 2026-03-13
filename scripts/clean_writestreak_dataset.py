from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", default="data/processed/writestreak_posts_base_clean.csv")
    ap.add_argument("--outfile", default="data/processed/writestreak_posts_final_clean.csv")
    args = ap.parse_args()

    df = pd.read_csv(args.infile)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")

    title = df["title"].fillna("").astype(str).str.strip()
    body = df["selftext"].fillna("").astype(str).str.strip()

    df["text"] = np.where(title.ne(""), (title + "\n\n" + body).str.strip(), body)
    df = df[df["text"].fillna("").astype(str).str.strip().ne("")].copy()

    token_re = re.compile(r"[A-Za-z']+")
    df["tokens"] = df["text"].astype(str).str.lower().map(lambda t: token_re.findall(t))
    df["n_tokens"] = df["tokens"].map(len)
    df["n_chars"] = df["text"].map(len)

    df = df.sort_values(["user_id", "created_at", "post_id"]).copy()
    df["post_index"] = df.groupby("user_id").cumcount() + 1
    first_time = df.groupby("user_id")["created_at"].transform("min")
    df["days_since_first"] = (df["created_at"] - first_time).dt.days
    df["user_post_count"] = df.groupby("user_id")["post_id"].transform("count")

    df["tokens"] = df["tokens"].map(json.dumps)

    Path(args.outfile).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.outfile, index=False)

    print("Wrote:", args.outfile)
    print("posts:", len(df), "users:", df["user_id"].nunique())


if __name__ == "__main__":
    main()