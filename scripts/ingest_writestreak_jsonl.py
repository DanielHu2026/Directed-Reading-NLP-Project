from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
from l2affect.utils.config import load_config, resolve

def stable_user_id(author: str) -> str:
    h = hashlib.sha256(author.encode("utf-8")).hexdigest()
    return h[:16]

def is_removed(text: str) -> bool:
    t = (text or "").strip().lower()
    return t == "" or t in {"[deleted]", "[removed]"}

def read_jsonl_files(folder: Path, max_lines: int | None = None) -> list[dict]:
    files = sorted(folder.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No .jsonl files found in: {folder}")
    rows = []
    n = 0
    for fp in files:
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                n += 1
                if max_lines and n > max_lines:
                    return rows
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                r["_source_file"] = fp.name
                rows.append(r)
    return rows

def ingest_posts(posts_dir: Path, max_lines: int | None = None) -> pd.DataFrame:
    raw = read_jsonl_files(posts_dir, max_lines=max_lines)

    rows = []
    for r in raw:
        # Reddit submissions often use: id, author, created_utc, title, selftext, permalink
        post_id = r.get("id")
        author = str(r.get("author", ""))
        created_utc = r.get("created_utc", None)

        title = r.get("title", "") or ""
        selftext = r.get("selftext", "") or ""
        if is_removed(selftext) and (title.strip() == ""):
            continue

        rows.append(
            {
                "post_id": post_id,
                "post_fullname": f"t3_{post_id}" if post_id else None,
                "author": author,
                "user_id": stable_user_id(author),
                "created_utc": created_utc,
                "created_at": pd.to_datetime(created_utc, unit="s", utc=True) if created_utc else pd.NaT,
                "title": title,
                "selftext": selftext,
                "subreddit": r.get("subreddit"),
                "permalink": r.get("permalink"),
                "score": r.get("score"),
                "num_comments": r.get("num_comments"),
                "source_file": r.get("_source_file"),
            }
        )

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["post_id"]).drop_duplicates(subset=["post_id"])
    df = df.sort_values(["created_at", "post_id"])
    return df

def ingest_comments(comments_dir: Path, max_lines: int | None = None) -> pd.DataFrame:
    raw = read_jsonl_files(comments_dir, max_lines=max_lines)

    rows = []
    for r in raw:
        comment_id = r.get("id")
        author = str(r.get("author", ""))
        created_utc = r.get("created_utc", None)
        body = r.get("body", "") or ""
        if is_removed(body):
            continue

        # link_id points to submission fullname: t3_xxxxx
        link_id = r.get("link_id")
        parent_id = r.get("parent_id")

        # quick correction-markup signals (often used by correctors)
        n_strike = body.count("~~") // 2
        n_bold = body.count("**") // 2
        has_markup = (n_strike > 0) or (n_bold > 0)

        rows.append(
            {
                "comment_id": comment_id,
                "comment_fullname": f"t1_{comment_id}" if comment_id else None,
                "author": author,
                "user_id": stable_user_id(author),
                "created_utc": created_utc,
                "created_at": pd.to_datetime(created_utc, unit="s", utc=True) if created_utc else pd.NaT,
                "body": body,
                "link_id": link_id,
                "parent_id": parent_id,
                "subreddit": r.get("subreddit"),
                "permalink": r.get("permalink"),
                "score": r.get("score"),
                "is_submitter": r.get("is_submitter"),
                "has_correction_markup": has_markup,
                "n_strikethrough": n_strike,
                "n_bold": n_bold,
                "source_file": r.get("_source_file"),
            }
        )

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["comment_id"]).drop_duplicates(subset=["comment_id"])
    df = df.sort_values(["created_at", "comment_id"])
    return df

def build_comment_to_post_index(posts: pd.DataFrame, comments: pd.DataFrame) -> pd.DataFrame:
    """
    Links comments to posts via comments.link_id == posts.post_fullname (usually t3_<post_id>).
    Produces per-post counts + correction-like counts.
    """
    # Normalize join keys
    posts_key = posts[["post_id", "post_fullname"]].dropna().copy()
    comments_key = comments[["comment_id", "link_id", "has_correction_markup"]].dropna().copy()

    merged = comments_key.merge(posts_key, left_on="link_id", right_on="post_fullname", how="inner")

    per_post = merged.groupby("post_id").agg(
        n_comments=("comment_id", "count"),
        n_correction_like=("has_correction_markup", "sum"),
    ).reset_index()

    return per_post

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--max-lines", type=int, default=None, help="For quick testing")
    args = ap.parse_args()

    cfg = load_config(args.config)
    posts_dir = resolve(cfg["inputs"]["writestreak_posts_jsonl_dir"])
    comments_dir = resolve(cfg["inputs"]["writestreak_comments_jsonl_dir"])
    processed_dir = resolve(cfg["paths"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    posts = ingest_posts(posts_dir, max_lines=args.max_lines)
    comments = ingest_comments(comments_dir, max_lines=args.max_lines)

    posts_out = processed_dir / "writestreak_posts_base.csv"
    comments_out = processed_dir / "writestreak_comments_base.csv"
    posts.to_csv(posts_out, index=False)
    comments.to_csv(comments_out, index=False)

    print("Wrote:", posts_out, f"(n={len(posts)})")
    print("Wrote:", comments_out, f"(n={len(comments)})")

    if "post_fullname" in posts.columns and "link_id" in comments.columns:
        idx = build_comment_to_post_index(posts, comments)
        idx_out = processed_dir / "writestreak_post_comment_index.csv"
        idx.to_csv(idx_out, index=False)
        print("Wrote:", idx_out, f"(n_posts_with_comments={len(idx)})")

if __name__ == "__main__":
    main()