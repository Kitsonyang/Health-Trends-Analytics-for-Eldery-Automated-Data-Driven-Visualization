"""
Category management routes.

- List, create, update, and delete categories with validation
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Any, Dict
from utils.shared import get_db_connection

router = APIRouter()


@router.get('/api/categories')
def list_categories():
    """Summary: List categories (alphabetical).
    Returns: {ok, items[]}"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT `id`, `category` FROM `category` ORDER BY `category` ASC")
        rows = cursor.fetchall()
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


@router.post('/api/categories')
def create_category(payload: Dict[str, Any] = Body(default={})):
    """Summary: Create category with validation and duplicate check.
    Returns: {ok, created, item}"""
    name = (payload.get('category') or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail='category must not be empty')
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check for existing category (case-insensitive)
        cursor.execute("SELECT `id`, `category` FROM `category` WHERE LOWER(`category`) = LOWER(%s) LIMIT 1", (name,))
        row = cursor.fetchone()
        if row:
            return {'ok': True, 'created': False, 'item': row}
        # Insert new category
        cursor.execute("INSERT INTO `category` (`category`) VALUES (%s)", (name,))
        conn.commit()
        new_id = cursor.lastrowid
        return {'ok': True, 'created': True, 'item': {'id': new_id, 'category': name}}
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


@router.put('/api/categories/{cat_id}')
@router.patch('/api/categories/{cat_id}')
def update_category(cat_id: int, payload: Dict[str, Any] = Body(default={})):
    """Summary: Update category name; validate existence and conflicts.
    Returns: {ok, item}"""
    name = (payload.get('category') or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail='category must not be empty')
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if category exists
        cursor.execute("SELECT `id` FROM `category` WHERE `id`=%s", (cat_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail='Category not found')
        # Check for name conflicts with other categories
        cursor.execute("SELECT `id` FROM `category` WHERE LOWER(`category`)=LOWER(%s) AND `id`<>%s", (name, cat_id))
        if cursor.fetchone() is not None:
            raise HTTPException(status_code=409, detail='Category name already exists')
        # Update category name
        cursor.execute("UPDATE `category` SET `category`=%s WHERE `id`=%s", (name, cat_id))
        conn.commit()
        return {'ok': True, 'item': {'id': cat_id, 'category': name}}
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


@router.delete('/api/categories/{cat_id}')
def delete_category(cat_id: int):
    """Summary: Delete category; orphan related symptoms first.
    Returns: {ok, affected_symptoms_set_null, deleted_category_id}"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Count symptoms that will be orphaned
        cursor.execute("SELECT COUNT(*) AS cnt FROM `symptom_categories` WHERE `category_id`=%s", (cat_id,))
        cnt_row = cursor.fetchone() or {'cnt': 0}
        affected = int(cnt_row.get('cnt', 0))
        # Orphan associated symptoms (set category_id to NULL)
        if affected:
            cursor.execute("UPDATE `symptom_categories` SET `category_id`=NULL WHERE `category_id`=%s", (cat_id,))
        # Delete category
        cursor.execute("DELETE FROM `category` WHERE `id`=%s", (cat_id,))
        conn.commit()
        return {'ok': True, 'affected_symptoms_set_null': affected, 'deleted_category_id': cat_id}
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


