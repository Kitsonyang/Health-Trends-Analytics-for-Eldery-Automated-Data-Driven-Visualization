from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import threading

import pandas as pd
import pymysql

from config import load_db_config
from services import cluster_usage  # models and interpretations
from services.model_usage import SVDNutritionalRiskPredictor


# Upload directory and image paths
BASE_DIR = Path(__file__).parent.parent  # backend directory
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

HEATMAP_PATH = BASE_DIR / "ml" / "outputs" / "rf_conditions_heatmap.png"
SIZES_PATH = BASE_DIR / "ml" / "outputs" / "cluster_sizes.png"
DEMOS_PATH = BASE_DIR / "ml" / "outputs" / "demographics_comparison.png"

DISPLAY_RENDER_LOCK = threading.Lock()


# Expected CSV columns
EXPECTED_COLUMNS: List[str] = [
    "PersonID",
    "Start date",
    "End date",
    "M-Risk Factors",
    "Gender",
    "Age",
    "MNA",
    "BMI",
    "Weight",
]


def normalize_name(name: str) -> str:
    if name is None:
        return ""
    return (
        str(name).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    )


def get_db_connection():
    cfg = load_db_config()
    return pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        charset='utf8mb4',
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_database_exists() -> None:
    """Create target database if it does not exist.

    Connects without selecting a database first, then creates the
    configured database with UTF8MB4 if missing.
    """
    cfg = load_db_config()
    conn = None
    cur = None
    try:
        conn = pymysql.connect(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            charset='utf8mb4',
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg.database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def ensure_schema_initialized(sql_file: Optional[Path] = None) -> None:
    """Summary: Ensure schema exists; run SQL if empty.
    Args: sql_file: Optional path to SQL file (default: dashboard.sql)"""
    base_dir = Path(__file__).parent.parent
    default_sql = base_dir / "data" / "sql" / "dashboard.sql"
    sql_path = Path(sql_file) if sql_file else default_sql

    # Ensure target database exists first
    ensure_database_exists()

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check existing tables in current database
        cur.execute("SELECT COUNT(*) AS cnt FROM information_schema.tables WHERE table_schema = DATABASE()")
        row = cur.fetchone() or {"cnt": 0}
        table_count = int(row.get("cnt", 0))
        if table_count > 0:
            return

        if not sql_path.exists():
            raise FileNotFoundError(f"Initialization SQL not found: {sql_path}")

        sql_text = sql_path.read_text(encoding="utf-8")

        # Naive split by semicolon; skip empty/whitespace-only statements
        statements = [s.strip() for s in sql_text.split(";") if s.strip()]
        for stmt in statements:
            cur.execute(stmt)

        conn.commit()
        print(f"Database initialized from {sql_path}")
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"Error during schema initialization: {exc}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_db_columns(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM `data`")
    cols = [r['Field'] for r in cur.fetchall()]
    cur.close()
    return cols


def map_expected_to_db_columns(db_cols: List[str]) -> Dict[str, Optional[str]]:
    db_map = {normalize_name(c): c for c in db_cols}
    mapping: Dict[str, Optional[str]] = {}
    for exp in EXPECTED_COLUMNS:
        key = normalize_name(exp)
        mapping[exp] = db_map.get(key)
    return mapping


def map_csv_headers_to_expected(csv_cols: List[str]) -> Dict[str, Optional[str]]:
    csv_map = {normalize_name(c): c for c in csv_cols}
    mapping: Dict[str, Optional[str]] = {}
    for exp in EXPECTED_COLUMNS:
        mapping[exp] = csv_map.get(normalize_name(exp))
    return mapping


def parse_date_to_iso(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in {"none", "nan", "null"}:
        return None
    fmts = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"]
    for f in fmts:
        try:
            return datetime.strptime(s, f).date().isoformat()
        except Exception:
            pass
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if pd.isna(dt):
            return None
        return dt.date().isoformat()
    except Exception:
        return None


def normalize_token(token: str) -> str:
    return token.strip().lower() if isinstance(token, str) else str(token).strip().lower()


def parse_risk_factors(cell_value) -> list:
    if cell_value is None:
        return []
    if isinstance(cell_value, (bytes, bytearray)):
        try:
            cell_value = cell_value.decode('utf-8', errors='ignore')
        except Exception:
            cell_value = str(cell_value)
    text = str(cell_value).strip()
    if not text:
        return []
    if text.lower() in {'none', 'no', 'n/a', 'na', 'null'}:
        return []
    parts = [p.strip() for p in text.split(',')]
    parts = [p for p in parts if p]
    return parts


def ensure_models_loaded() -> None:
    if not all([
        cluster_usage.svd_model is not None,
        cluster_usage.clustering_model is not None,
        cluster_usage.rf_columns is not None
    ]):
        (svd, clu, rfs, interp) = cluster_usage.load_patient_models("patient_classifier_model.pkl")
        if not all([svd, clu, rfs]):
            raise RuntimeError("Models not loaded. Check pickle path/format.")
        cluster_usage.svd_model = svd
        cluster_usage.clustering_model = clu
        cluster_usage.rf_columns = rfs
        cluster_usage.cluster_interpretations = interp or {}


# Predictor singleton
predictor = SVDNutritionalRiskPredictor()
predictor.load_trained_components()


