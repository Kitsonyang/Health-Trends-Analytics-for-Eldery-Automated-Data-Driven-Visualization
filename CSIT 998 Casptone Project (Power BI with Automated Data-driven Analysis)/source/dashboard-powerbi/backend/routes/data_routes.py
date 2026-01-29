"""
Data stats endpoints.

- Returns total rows and unique patient count from `data` table
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from utils.shared import get_db_connection

router = APIRouter()


@router.get('/api/data/stats')
def data_stats():
    """Summary: Get overall stats.
    Returns: {ok, total_rows, unique_persons}"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Count total records
        cursor.execute("SELECT COUNT(*) AS cnt FROM `data`")
        total_row = cursor.fetchone() or { 'cnt': 0 }
        total_rows = int(total_row.get('cnt', 0))

        # Count unique patients (excluding empty/whitespace PersonIDs)
        cursor.execute("SELECT COUNT(DISTINCT NULLIF(TRIM(`PersonID`), '')) AS cnt FROM `data`")
        person_row = cursor.fetchone() or { 'cnt': 0 }
        unique_persons = int(person_row.get('cnt', 0))

        return { 'ok': True, 'total_rows': total_rows, 'unique_persons': unique_persons }
    except Exception as e:
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


