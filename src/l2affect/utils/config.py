from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import yaml

def repo_root() -> Path:
    # file is src/l2affect/utils/config.py
    return Path(__file__).resolve().parents[3]

def load_config(path: str | Path) -> Dict[str, Any]:
    path = Path(path)
    if not path.is_absolute():
        path = repo_root() / path
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (repo_root() / p).resolve()
