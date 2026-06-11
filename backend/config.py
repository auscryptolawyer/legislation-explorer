"""Centralised configuration."""
from __future__ import annotations

import os
from pathlib import Path

# Base paths
BASE = Path.home() / "legislation-explorer"
DATA_DIR = BASE / "data"
FRONTEND_DIST = BASE / "frontend" / "dist"
SEARCH_DB = BASE / "search_index.db"

# External data directories
COMMENTARY_DIR = Path(
    os.environ.get(
        "COMMENTARY_DIR",
        "/home/harrison/projects/cadena-knowledge-MCP/pipeline/output",
    )
)
CASE_DIR = Path(
    os.environ.get("CASE_DIR", "/home/harrison/projects/asic-scraper/cases")
)
RULING_DIR = Path(
    os.environ.get(
        "RULING_DIR",
        "/home/harrison/projects/cadena-knowledge-MCP/data/rulings",
    )
)
ATO_RULING_DIR = Path(
    os.environ.get(
        "ATO_RULING_DIR",
        "/home/harrison/projects/cadena-knowledge-MCP/data/ato_rulings",
    )
)

# Security
BEARER_TOKEN = os.environ.get("LEGISLATION_BEARER_TOKEN")
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS",
        "https://legislation.scriptkitty.yachts,http://localhost:5173,http://localhost:3000",
    ).split(",")
    if o.strip()
]

# Publication names for commentary
PUBLICATION_NAMES = {
    "master_tax_guide.json": "Master Tax Guide",
    "master_gst_guide.json": "Master GST Guide",
    "master_tax_examples.json": "Master Tax Examples",
}

PUB_ACT_MAP = {
    "master_tax_guide.json": "master-tax-guide",
    "master_gst_guide.json": "master-gst-guide",
    "master_tax_examples.json": "master-tax-examples",
}
