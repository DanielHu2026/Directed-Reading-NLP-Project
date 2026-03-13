# L2 Affect Gap → LBA Sensitivity 


## Quickstart

### Create environment (pip)
```bash
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows (powershell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Validate config + create folders
```bash
python scripts/validate_setup.py --config configs/config.yaml
```

## Folder layout
- `configs/` : configuration files (paths, filenames, thresholds)
- `src/` : Python package code
- `data/raw/` : raw inputs (lexicons, reddit export) - not committed
- `data/processed/` : derived outputs - not committed
- `reports/figures/`, `reports/tables/` : exported artifacts for the report
- `notebooks/` : analysis
- `scripts/` : helper scripts (validation, download helpers, etc.)
