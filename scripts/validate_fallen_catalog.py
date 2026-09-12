"""Build-time validation for the shared Gathering Of The Fallen catalog."""

import os
import sys
from pathlib import Path

os.environ.setdefault("TELEGRAM_TOKEN", "123456:CATALOGCHECK")
os.environ.setdefault("OPENAI_API_KEY", "catalog-validation-placeholder")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main


catalog = main._load_catalog()
print(
    "Validated shared catalog: "
    f"{len(catalog['tracks']) + len(catalog['videos'])} tracks, "
    f"{len(catalog['videos'])} videos, {len(catalog['releases'])} releases."
)