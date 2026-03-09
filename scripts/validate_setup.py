from __future__ import annotations
import argparse
from pathlib import Path

from l2affect.utils.config import load_config, resolve, repo_root

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def main() -> None:
    ap = argparse.ArgumentParser(description="Validate config + ensure directories exist.")
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)

    # ensure key dirs
    ensure_dir(resolve(cfg["paths"]["raw_dir"]))
    ensure_dir(resolve(cfg["paths"]["processed_dir"]))
    ensure_dir(resolve(cfg["paths"]["reports_figures_dir"]))
    ensure_dir(resolve(cfg["paths"]["reports_tables_dir"]))

    print("Repo root:", repo_root())
    print("Config:", resolve(args.config))
    print("\nResolved paths:")
    for k, v in cfg["paths"].items():
        print(f"  {k}: {resolve(v)}")

    print("\nInputs (expected locations):")
    for k, v in cfg["inputs"].items():
        print(f"  {k}: {resolve(v)}")

    print("\nOK: setup validated (folders created if missing).")

if __name__ == "__main__":
    main()
