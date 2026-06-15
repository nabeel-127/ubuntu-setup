from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
SOFTWARE_CONFIG = CONFIG_DIR / "software.yaml"
CATEGORIES_CONFIG = CONFIG_DIR / "categories.yaml"
SOURCES_CONFIG = CONFIG_DIR / "sources.yaml"
LOGGING_CONFIG = CONFIG_DIR / "logging.yaml"
