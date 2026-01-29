from __future__ import annotations
import types, tempfile, sys
from pathlib import Path
import os
from datetime import datetime
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# Minimal fake DB (stateless)

class _FakeCursor:
    def __init__(self):
        self._rows = []
        self._lastrowid = 1
        self.rowcount = 0

    def execute(self, sql: str, params=None):
        self.rowcount = 0

        # ---- Categories (list/create/uniqueness/delete) ----
        if "FROM `category`" in sql and "WHERE" not in sql and "COUNT" not in sql and "JOIN" not in sql:
            # Return a small static list; tests only assert 200/ok and POST echo
            self._rows = [{'id': 1, 'category': 'Digestive'}, {'id': 2, 'category': 'General'}]
        elif "SELECT `id`, `category` FROM `category` WHERE LOWER(`category`)=LOWER" in sql:
            # Uniqueness check returns None → no duplicate
            self._rows = None
        elif "INSERT INTO `category`" in sql:
            self._lastrowid += 1
            self.rowcount = 1
            self._rows = []
        elif "DELETE FROM `category` WHERE `id`=" in sql:
            self.rowcount = 1
            self._rows = []

        # ---- Data stats used by /api/data/stats (nonfunctional) ----
        elif "SELECT COUNT(*) AS cnt FROM `data`" in sql:
            self._rows = {'cnt': 10}
        elif "SELECT COUNT(DISTINCT NULLIF(TRIM(`PersonID`)" in sql:
            self._rows = {'cnt': 5}

        elif "INSERT INTO `data` (" in sql:
            # Pretend all rows were inserted
            self.rowcount = 2
            self._rows = []

        # ---- Risk columns / simple selects that routes may use ----
        elif "FROM `data` WHERE" in sql:
            self._rows = [{'risk': 'bruise, pain'}, {'risk': 'constipation'}]

        else:
            self._rows = []

        return self

    def executemany(self, sql, seq):
        self.rowcount = len(list(seq))

    def fetchall(self):
        if isinstance(self._rows, list):
            return self._rows
        return [self._rows] if self._rows else []

    def fetchone(self):
        if isinstance(self._rows, list):
            return self._rows[0] if self._rows else None
        return self._rows

    @property
    def lastrowid(self):
        return self._lastrowid


class _FakeConn:
    def __init__(self):
        self._cursor = _FakeCursor()
    def cursor(self): return self._cursor
    def commit(self): pass
    def rollback(self): pass
    def close(self): pass

def get_db_connection():
    # Stateless per call is fine for current tests
    return _FakeConn()


# "shared" module shims

EXPECTED_COLUMNS = [
    'PersonID', 'Start date', 'End date', 'M-Risk Factors',
    'Gender', 'Age', 'MNA', 'BMI', 'Weight'
]

def get_db_columns(_conn): return EXPECTED_COLUMNS
def map_expected_to_db_columns(db_cols): return {c: c for c in EXPECTED_COLUMNS if c in db_cols}
def map_csv_headers_to_expected(csv_cols): return {c: (c if c in csv_cols else None) for c in EXPECTED_COLUMNS}

def parse_date_to_iso(val):
    s = "" if val is None else str(val).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return None

def ensure_models_loaded(): return True  # for /healthz
def normalize_token(s): return (s or "").strip().lower()
def parse_risk_factors(s: str): return [p.strip() for p in (s or "").split(",") if p.strip()]

class _Predictor:
    def predict_patient_risk(self, age, gender, patient_conditions, include_details=False):
        return {"score": 0.42, "age": age, "gender": gender, "n_conds": len(patient_conditions or {})}
predictor = _Predictor()

# Temp dir & paths used by import
_TMP = Path(tempfile.gettempdir()) / "pytest_minimal"
_TMP.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR   = _TMP

# Install shims as the "shared" module (and alias to utils.shared used by app code)
_fake_shared = types.ModuleType("shared")
for k, v in {
    "get_db_connection": get_db_connection,
    "map_expected_to_db_columns": map_expected_to_db_columns,
    "map_csv_headers_to_expected": map_csv_headers_to_expected,
    "get_db_columns": get_db_columns,
    "EXPECTED_COLUMNS": EXPECTED_COLUMNS,
    "UPLOAD_DIR": UPLOAD_DIR,
    "parse_date_to_iso": parse_date_to_iso,
    "normalize_token": normalize_token,
    "parse_risk_factors": parse_risk_factors,
    "ensure_models_loaded": ensure_models_loaded,
    "predictor": predictor,
}.items():
    setattr(_fake_shared, k, v)
sys.modules["shared"] = _fake_shared
# Ensure backend imports like `from utils.shared import ...` resolve to our shim
sys.modules["utils.shared"] = _fake_shared


# Ensure project module path available (backend directory)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
for _p in [str(_BACKEND_DIR), str(_ROOT_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


# Fixtures & router helper

@pytest.fixture
def app() -> FastAPI:
    return FastAPI()

@pytest.fixture
def client(app):
    return TestClient(app)

def mount_router(app: FastAPI, module_path: str, attr: str = "router"):
    """Include a router from 'routes.xxx' into a fresh app."""
    try:
        mod = __import__(module_path, fromlist=[attr])
    except ModuleNotFoundError:
        # Fallback to 'backend.routes.xxx' when tests run from repo root
        alt = f"backend.{module_path}"
        mod = __import__(alt, fromlist=[attr])
    app.include_router(getattr(mod, attr))
    return app
