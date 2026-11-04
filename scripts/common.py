"""Shared paths for the six learning scripts. No data transformation happens here."""

import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = Path(os.environ["FRESH_RETAIL_TRAIN"]) if "FRESH_RETAIL_TRAIN" in os.environ else ROOT / "data" / "train.parquet"
ARTIFACTS = ROOT / "artifacts"


def check_data() -> Path:
    if not DATA.is_file():
        raise FileNotFoundError(f"找不到训练数据：{DATA}")
    return DATA


def output_dir() -> Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    return ARTIFACTS
