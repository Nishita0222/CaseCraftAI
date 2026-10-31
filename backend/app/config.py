"""Configuration. All data stays on the local disk (SQLite + folders under ./data)."""
import os
from pathlib import Path

ALLOWED_EXT = {".pdf", ".docx", ".xlsx", ".xlsm", ".eml", ".txt", ".md", ".csv"}
MAX_UPLOAD_MB = 25


def data_dir() -> Path:
    base = os.environ.get("CASESTUDY_DATA_DIR")
    return Path(base) if base else Path(__file__).resolve().parent.parent / "data"


def db_path() -> Path:
    return data_dir() / "casestudy.db"


def upload_dir() -> Path:
    return data_dir() / "uploads"


def output_dir() -> Path:
    return data_dir() / "outputs"


def export_dir() -> Path:
    return data_dir() / "exports"


def ensure_dirs() -> None:
    for p in (data_dir(), upload_dir(), output_dir(), export_dir()):
        p.mkdir(parents=True, exist_ok=True)
