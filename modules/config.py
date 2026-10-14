"""Loads credentials without ever putting them in Git.

Lookup order:
1. No_sync/secrets.toml  (local computer; the folder is git-ignored)
2. st.secrets            (Streamlit Cloud; pasted into App settings -> Secrets)
"""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # project root
SECRETS_FILE = ROOT / "No_sync" / "secrets.toml"


def get_secrets() -> dict:
    """Return all secrets as a dict, e.g. secrets['mongo']['user']."""
    if SECRETS_FILE.exists():
        return tomllib.loads(SECRETS_FILE.read_text())
    try:
        import streamlit as st
        return {k: dict(v) for k, v in st.secrets.items()}   # raises if no secrets set
    except Exception as exc:
        raise RuntimeError(
            f"No credentials found. Create {SECRETS_FILE} (see secrets.example.toml) "
            "or add them under Secrets in the Streamlit Cloud app settings."
        ) from exc
