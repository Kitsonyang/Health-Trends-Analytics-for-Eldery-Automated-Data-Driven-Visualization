"""
Symptom management routes.

- Insert/list/update/rename/delete symptoms; extract from risk factors
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Any, Dict, Optional, Set
from utils.shared import get_db_connection, normalize_token, parse_risk_factors, get_db_columns

router = APIRouter()


@router.post('/api/symptoms/insert_many')
def insert_many_symptoms(payload: Dict[str, Any] = Body(default={})):
    """Summary: Batch insert symptoms with category validation/dedup.
    Returns: {ok, requested, inserted, skipped_existing, items_inserted, items_skipped}"""
    items = payload.get('items') or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail='items must not be empty')

    def norm(s: str) -> str:
        """Normalize symptom for duplicate detection."""
        return (s or '').strip().lower()

    # Deduplicate input items (case-insensitive, latest category_id wins)
    merged: Dict[str, Optional[int]] = {}
    clean_items = []
    for it in items:
        sym = (it.get('symptom') or '').strip()
        cid = it.get('category_id')
        if not sym or cid is None:
            continue
        try:
            cid = int(cid)
        except Exception:
            continue
        clean_items.append({'symptom': sym, 'category_id': int(cid)})
        merged[norm(sym)] = int(cid)

    if not merged:
        raise HTTPException(status_code=400, detail='No valid items')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validate all category IDs exist
        cursor.execute("SELECT `id` FROM `category`")
        valid_category_ids = {row['id'] for row in cursor.fetchall()}
        invalid_category_ids = sorted({cid for cid in merged.values() if cid not in valid_category_ids})
        if invalid_category_ids:
            raise HTTPException(status_code=400, detail={'ok': False, 'error': 'Invalid category_id exists', 'invalid_category_ids': invalid_category_ids})

        # Load existing symptoms (case-insensitive)
        cursor.execute("SELECT `symptom` FROM `symptom_categories`")
        existing = {norm(row['symptom']) for row in cursor.fetchall() if row.get('symptom') is not None}

        # Filter out duplicates, preserve original capitalization
        to_insert_pairs = []
        items_inserted = []
        items_skipped = []
        for sym_norm, cid in merged.items():
            if sym_norm in existing:
                items_skipped.append(sym_norm)
                continue
            # Find original capitalization from clean_items
            original_symptom = next((ci['symptom'] for ci in clean_items if norm(ci['symptom']) == sym_norm), sym_norm)
            to_insert_pairs.append((original_symptom, cid))
            items_inserted.append(original_symptom)

        # Batch insert new symptoms
        inserted_count = 0
        if to_insert_pairs:
            cursor.executemany(
                "INSERT INTO `symptom_categories` (`symptom`, `category_id`) VALUES (%s, %s)",
                to_insert_pairs,
            )
            conn.commit()
            inserted_count = len(to_insert_pairs)

        return {
            'ok': True,
            'requested': len(merged),
            'inserted': inserted_count,
            'skipped_existing': len(items_skipped),
            'items_inserted': items_inserted,
            'items_skipped': items_skipped,
        }
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


@router.get('/api/symptoms')
def list_symptoms(search: str = Query(default=''), unassigned: bool = Query(default=False), category_id: Optional[int] = Query(default=None)):
    """Summary: List symptoms with filters.
    Returns: {ok, items[]}"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        sql = (
            "SELECT sc.`symptom`, sc.`category_id`, c.`category` "
            "FROM `symptom_categories` sc "
            "LEFT JOIN `category` c ON sc.`category_id` = c.`id` "
            "WHERE 1=1"
        )
        params: list = []
        if search:
            sql += " AND sc.`symptom` LIKE %s"
            params.append(f"%{search}%")
        if unassigned:
            sql += " AND sc.`category_id` IS NULL"
        if category_id is not None:
            sql += " AND sc.`category_id`=%s"
            params.append(int(category_id))
        sql += " ORDER BY sc.`symptom` ASC"
        cursor.execute(sql, params)
        rows = cursor.fetchall() or []
        return {'ok': True, 'items': rows}
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


@router.post('/api/symptoms/update_many')
def update_many_symptoms(payload: Dict[str, Any] = Body(default={})):
    """Summary: Batch reassign categories; validate IDs; skip no-ops.
    Returns: {ok, updated, skipped, items_updated, items_skipped}"""
    items = payload.get('items') or []
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail='items must not be empty')
    normalized = []
    for it in items:
        sym = (it.get('symptom') or '').strip()
        cid = it.get('category_id', None)
        if sym == '':
            continue
        if cid is not None:
            try:
                cid = int(cid)
            except Exception:
                cid = None
        normalized.append({'symptom': sym, 'category_id': cid})
    if not normalized:
        raise HTTPException(status_code=400, detail='No valid items')
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT `id` FROM `category`")
        valid_category_ids = {row['id'] for row in cursor.fetchall()}
        invalid_category_ids = sorted({it['category_id'] for it in normalized if it['category_id'] is not None and it['category_id'] not in valid_category_ids})
        if invalid_category_ids:
            raise HTTPException(status_code=400, detail={'ok': False, 'error': 'Invalid category_id exists', 'invalid_category_ids': invalid_category_ids})
        updated = 0
        skipped = 0
        items_updated = []
        items_skipped = []
        for it in normalized:
            sym = it['symptom']
            cid = it['category_id']
            cursor.execute("SELECT `category_id` FROM `symptom_categories` WHERE `symptom`=%s", (sym,))
            cur = cursor.fetchone()
            if cur is None:
                items_skipped.append(sym)
                continue
            if cur['category_id'] == cid:
                items_skipped.append(sym)
                skipped += 1
                continue
            cursor.execute("UPDATE `symptom_categories` SET `category_id`=%s WHERE `symptom`=%s", (cid, sym))
            items_updated.append(sym)
            updated += 1
        conn.commit()
        return {'ok': True, 'updated': updated, 'skipped': skipped, 'items_updated': items_updated, 'items_skipped': items_skipped}
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


@router.post('/api/symptoms/rename')
def rename_symptom(payload: Dict[str, Any] = Body(default={})):
    """Summary: Rename symptom; reject conflicts/empty names.
    Returns: {ok, updated}"""
    old_symptom = (payload.get('old_symptom') or '').strip()
    new_symptom = (payload.get('new_symptom') or '').strip()
    if not old_symptom or not new_symptom:
        raise HTTPException(status_code=400, detail='old_symptom/new_symptom must not be empty')
    if old_symptom == new_symptom:
        return {'ok': True, 'updated': 0}
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM `symptom_categories` WHERE LOWER(`symptom`) = LOWER(%s) AND `symptom` <> %s LIMIT 1", (new_symptom, old_symptom))
        if cursor.fetchone() is not None:
            raise HTTPException(status_code=409, detail='Target symptom name already exists')
        cursor.execute("UPDATE `symptom_categories` SET `symptom`=%s WHERE `symptom`=%s", (new_symptom, old_symptom))
        conn.commit()
        return {'ok': True, 'updated': cursor.rowcount}
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


@router.post('/api/symptoms/delete')
def delete_symptom(payload: Dict[str, Any] = Body(default={})):
    """Summary: Delete symptom (idempotent).
    Returns: {ok, deleted}"""
    sym = (payload.get('symptom') or '').strip()
    if not sym:
        raise HTTPException(status_code=400, detail='symptom must not be empty')
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM `symptom_categories` WHERE `symptom`=%s", (sym,))
        conn.commit()
        return {'ok': True, 'deleted': cursor.rowcount}
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


@router.post('/api/process_risk_factors')
def process_risk_factors(dry_run: bool = Query(default=True), risk_col: str = Query(default='M-Risk Factors')):
    """Summary: Extract symptoms from risk column; dry-run supported.
    Returns: {ok, dry_run, risk_col, inserted, missing_items}"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate risk column exists in data table schema
        db_cols = get_db_columns(conn)
        if risk_col not in db_cols:
            raise HTTPException(status_code=400, detail=f'Column not found: {risk_col}')

        # Collect unique symptoms from risk factor column (exclude NULL/empty)
        cursor.execute(
            f"SELECT `{risk_col}` AS risk FROM `data` WHERE `{risk_col}` IS NOT NULL AND TRIM(`{risk_col}`) <> ''"
        )
        rows = cursor.fetchall() or []

        def norm(s: str) -> str:
            """Normalize for case-insensitive comparison."""
            return (s or '').strip().lower()

        # Parse and deduplicate symptoms (preserves first occurrence capitalization)
        found_map: Dict[str, str] = {}
        for row in rows:
            items = parse_risk_factors(row.get('risk'))
            for it in items:
                n = norm(it)
                if n and n not in found_map:
                    found_map[n] = it.strip()

        # Load existing symptoms from symptom_categories table
        cursor.execute("SELECT `symptom` FROM `symptom_categories`")
        existing_rows = cursor.fetchall() or []
        existing_norms: Set[str] = {norm(r.get('symptom')) for r in existing_rows if r.get('symptom') is not None}

        # Compute missing symptoms (found in data but not in symptom_categories)
        missing_norms = set(found_map.keys()) - existing_norms
        missing_items = sorted([found_map[n] for n in missing_norms])

        # Insert missing symptoms if not dry_run (category_id=NULL)
        inserted = 0
        if not dry_run and missing_items:
            pairs = [(mi, None) for mi in missing_items]
            cursor.executemany(
                "INSERT INTO `symptom_categories` (`symptom`, `category_id`) VALUES (%s, %s)",
                pairs,
            )
            conn.commit()
            inserted = len(pairs)

        return {
            'ok': True,
            'dry_run': bool(dry_run),
            'risk_col': risk_col,
            'inserted': inserted,
            'missing_items': missing_items,
        }
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


