import argparse
from pathlib import Path
import pandas as pd
import numpy as np

from l2affect.utils.config import load_config, resolve

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    in_path = resolve(cfg["inputs"]["lexicon_file"])
    out_dir = resolve(cfg["paths"]["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)

    # Expected data columns
    required = {"Word", "L2.Val.Mean", "L2.Aro.Mean", "L1.Val.Mean", "L1.Aro.Mean"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {missing}\nColumns found: {list(df.columns)}")

    df["word"] = df["Word"].astype(str).str.strip().str.lower()

    # Keep rows with both L1 and L2 valence+arousal means
    df = df.dropna(subset=["L2.Val.Mean", "L2.Aro.Mean", "L1.Val.Mean", "L1.Aro.Mean"]).copy()

    # Clean L2 table
    l2 = df[["word", "L2.Val.Mean", "L2.Aro.Mean", "L2.Val.SD", "L2.Aro.SD", "L2.Val.N", "L2.Aro.N", "Freq"]].copy()
    l2.columns = ["word", "valence", "arousal", "valence_sd", "arousal_sd", "valence_n", "arousal_n", "freq"]

    # Clean L1 table
    l1 = df[["word", "L1.Val.Mean", "L1.Aro.Mean", "L1.Val.SD", "L1.Aro.SD", "L1.Val.N", "L1.Aro.N", "Freq"]].copy()
    l1.columns = ["word", "valence", "arousal", "valence_sd", "arousal_sd", "valence_n", "arousal_n", "freq"]

    # Gap table
    gaps = pd.DataFrame({
        "word": df["word"],
        "valence_l1": df["L1.Val.Mean"].astype(float),
        "arousal_l1": df["L1.Aro.Mean"].astype(float),
        "valence_l2": df["L2.Val.Mean"].astype(float),
        "arousal_l2": df["L2.Aro.Mean"].astype(float),
    })
    gaps["gap_valence"] = gaps["valence_l2"] - gaps["valence_l1"]
    gaps["gap_arousal"] = gaps["arousal_l2"] - gaps["arousal_l1"]
    gaps["gap_mag"] = np.sqrt(gaps["gap_valence"]**2 + gaps["gap_arousal"]**2)

    # Write outputs
    l2_path = out_dir / "imbault_l2_clean_va.csv"
    l1_path = out_dir / "imbault_l1_clean_va.csv"
    gaps_path = out_dir / "imbault_gaps_va.csv"

    l2.to_csv(l2_path, index=False)
    l1.to_csv(l1_path, index=False)
    gaps.to_csv(gaps_path, index=False)

    print("Wrote:")
    print(" ", l2_path)
    print(" ", l1_path)
    print(" ", gaps_path)
    print(f"Rows kept (complete L1+L2 V/A): {len(gaps)}")

if __name__ == "__main__":
    main()