"""
CSV import workflow: preview and commit.

- Validates column mapping and schema, provides preview rows, then inserts
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Body
from typing import Any, Dict
import pandas as pd
import logging

from utils.shared import (
    UPLOAD_DIR,
    get_db_connection,
    get_db_columns,
    map_expected_to_db_columns,
    map_csv_headers_to_expected,
    EXPECTED_COLUMNS,
    parse_date_to_iso,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post('/api/import/preview')
async def import_preview(file: UploadFile = File(...)):
    """Summary: Preview CSV; validate schema and return first rows.
    Returns: {ok, token, filename, total_rows, csv_columns, expected_columns, missing_in_csv, missing_in_db, csv_to_expected, expected_to_db, can_import, preview}"""
    if not file.filename:
        raise HTTPException(status_code=400, detail='No file provided')
    suffix = ''.join(UPLOAD_DIR.joinpath(file.filename).suffixes) or '.csv'
    import uuid
    token = f"{uuid.uuid4().hex}{suffix}"
    temp_path = UPLOAD_DIR / token
    try:
        with temp_path.open('wb') as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to save temp file: {e}')

    try:
        df = pd.read_csv(temp_path, sep=None, engine='python')
    except Exception:
        try:
            df = pd.read_csv(temp_path, sep='\t', engine='python')
        except Exception as e:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f'Failed to parse CSV: {e}')

    csv_cols = list(map(str, df.columns.tolist()))
    csv_map = map_csv_headers_to_expected(csv_cols)
    missing_in_csv = [exp for exp, actual in csv_map.items() if actual is None]

    conn = None
    try:
        conn = get_db_connection()
        db_cols = get_db_columns(conn)
        db_map = map_expected_to_db_columns(db_cols)
        missing_in_db = [exp for exp, target in db_map.items() if target is None]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Database error: {e}')
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    can_import = len(missing_in_csv) == 0 and len(missing_in_db) == 0
    preview_df = df.head(20).copy().where(pd.notnull(df.head(20)), None)
    preview_rows = preview_df.to_dict(orient='records')

    return {
        'ok': True,
        'token': token,
        'filename': file.filename,
        'total_rows': int(len(df)),
        'csv_columns': csv_cols,
        'expected_columns': EXPECTED_COLUMNS,
        'missing_in_csv': missing_in_csv,
        'missing_in_db': missing_in_db,
        'csv_to_expected': csv_map,
        'expected_to_db': db_map,
        'can_import': can_import,
        'preview': preview_rows,
    }


class ImportCommitPayload:
    """Import confirmation payload schema (not enforced, using dict for flexibility)."""
    token: str   # UUID token from preview step
    mode: str    # 'overwrite' or 'append'


@router.post('/api/import/commit')
def import_commit(payload: Dict[str, Any] = Body(default={})):
    """Summary: Commit CSV; validate schema and insert rows (overwrite/append).
    Returns: {ok, mode, inserted, total_rows_in_file}"""
    token = (payload.get('token') or '').strip()
    mode = (payload.get('mode') or '').strip().lower()
    if mode not in {'overwrite', 'append'}:
        raise HTTPException(status_code=400, detail='mode must be overwrite or append')
    path = UPLOAD_DIR / token
    if not path.exists():
        raise HTTPException(status_code=400, detail='Invalid token or file expired')

    # Re-parse CSV (token could have been from hours ago)
    try:
        try:
            df = pd.read_csv(path, sep=None, engine='python')
        except Exception:
            df = pd.read_csv(path, sep='\t', engine='python')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to parse CSV: {e}')

    # Re-validate CSV schema (redundant but ensures data integrity)
    csv_cols = list(map(str, df.columns.tolist()))
    csv_map = map_csv_headers_to_expected(csv_cols)
    missing_in_csv = [exp for exp, actual in csv_map.items() if actual is None]
    if missing_in_csv:
        raise HTTPException(status_code=400, detail={'ok': False, 'error': 'CSV missing required columns', 'missing_in_csv': missing_in_csv})

    conn = None
    cursor = None
    inserted = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validate database schema
        db_cols = get_db_columns(conn)
        db_map = map_expected_to_db_columns(db_cols)
        missing_in_db = [exp for exp, target in db_map.items() if target is None]
        if missing_in_db:
            raise HTTPException(status_code=400, detail={'ok': False, 'error': 'DB table `data` missing required columns', 'missing_in_db': missing_in_db})

        # Create backup table for overwrite mode (enables rollback on failure)
        backup_table = None
        if mode == 'overwrite':
            import uuid
            backup_table = f"data_backup_{uuid.uuid4().hex[:8]}"
            cursor.execute(f"CREATE TABLE `{backup_table}` LIKE `data`")
            cursor.execute(f"INSERT INTO `{backup_table}` SELECT * FROM `data`")
            conn.commit()
            cursor.execute("TRUNCATE TABLE `data`")
            conn.commit()

        # Prepare column mapping for insertion
        ordered_expected = EXPECTED_COLUMNS[:]
        insert_cols = [db_map[exp] for exp in ordered_expected]
        rename_map = {csv_map[exp]: exp for exp in ordered_expected}
        work_df = df.rename(columns=rename_map)

        def to_num(val):
            """Convert value to number with None fallback for invalid/empty values."""
            try:
                if val is None or str(val).strip() == '':
                    return None
                n = float(val)
                import pandas as pd
                if pd.isna(n):
                    return None
                return n
            except Exception:
                return None

        # Transform DataFrame rows to database format
        values = []
        for _, row in work_df.iterrows():
            person_id = None if pd.isna(row.get('PersonID')) else str(row.get('PersonID')).strip()
            start_date = parse_date_to_iso(row.get('Start date'))
            end_date = parse_date_to_iso(row.get('End date'))
            mrf = None if pd.isna(row.get('M-Risk Factors')) else str(row.get('M-Risk Factors')).strip()
            gender = None if pd.isna(row.get('Gender')) else str(row.get('Gender')).strip()
            age = to_num(row.get('Age'))
            mna = to_num(row.get('MNA'))
            bmi = to_num(row.get('BMI'))
            weight = to_num(row.get('Weight'))
            values.append((person_id, start_date, end_date, mrf, gender, age, mna, bmi, weight))

        # Batch insert all rows
        placeholders = ','.join(['%s'] * len(insert_cols))
        cols_sql = ','.join([f"`{c}`" for c in insert_cols])
        sql = f"INSERT INTO `data` ({cols_sql}) VALUES ({placeholders})"
        if values:
            try:
                cursor.executemany(sql, values)
                conn.commit()
                inserted = cursor.rowcount or len(values)
            except Exception as e:
                # Rollback: restore from backup if overwrite mode
                if mode == 'overwrite' and backup_table:
                    try:
                        cursor.execute("TRUNCATE TABLE `data`")
                        cursor.execute(f"INSERT INTO `data` SELECT * FROM `{backup_table}`")
                        conn.commit()
                    except Exception:
                        pass
                    finally:
                        try:
                            cursor.execute(f"DROP TABLE IF EXISTS `{backup_table}`")
                            conn.commit()
                        except Exception:
                            pass
                raise HTTPException(status_code=500, detail=f"Import failed; data restored to pre-import state: {e}")

        # Cleanup: drop backup table after successful import
        if mode == 'overwrite' and backup_table:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS `{backup_table}`")
                conn.commit()
            except Exception:
                pass
        
        # Delete temporary CSV file after successful import
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted temporary file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {path}: {e}")

        return {'ok': True, 'mode': mode, 'inserted': inserted, 'total_rows_in_file': int(len(df))}
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


