from __future__ import annotations

import logging
from pathlib import Path

import yaml


def configure_logging(path: Path) -> None:
    if not path.exists():
        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
        return
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    level = getattr(logging, str(data.get("level", "INFO")).upper(), logging.INFO)
    fmt = str(data.get("format", "[%(levelname)s] %(message)s"))
    logging.basicConfig(level=level, format=fmt)
