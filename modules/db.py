"""MongoDB helpers (no Streamlit imports)."""
import urllib.parse

import certifi
from pymongo import MongoClient


def build_uri(user: str, password: str, host: str) -> str:
    """Build an Atlas connection string with safely encoded credentials."""
    u, p = urllib.parse.quote_plus(user), urllib.parse.quote_plus(password)
    return f"mongodb+srv://{u}:{p}@{host}/?retryWrites=true&w=majority&appName=Cluster0"


def get_client(uri: str) -> MongoClient:
    """certifi CA file avoids SSL errors on macOS."""
    return MongoClient(uri, tlsCAFile=certifi.where())
