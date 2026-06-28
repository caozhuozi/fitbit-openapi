from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PARSED = DATA / "parsed"
SAMPLES = DATA / "samples" / "sanitized"
PATHS = ROOT / "paths"
COMPONENTS = ROOT / "components"
SCHEMAS = COMPONENTS / "schemas"


def ensure_dirs() -> None:
    for path in [RAW, PARSED, SAMPLES, PATHS, COMPONENTS, SCHEMAS, ROOT / "dist"]:
        path.mkdir(parents=True, exist_ok=True)
