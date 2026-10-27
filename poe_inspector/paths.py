"""Where things live. APP: code, web files and the dat schema (read-only, may be in Program Files). DATA: poe2.db, caches, recordings (writable; in an installed copy this is %LOCALAPPDATA%\\PoE Inspector)."""
import os

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("POE_INSPECTOR_DATA") or APP
os.makedirs(DATA, exist_ok=True)
SCHEMA = os.path.join(APP, "schema.min.json")
DB = os.path.join(DATA, "poe2.db")
