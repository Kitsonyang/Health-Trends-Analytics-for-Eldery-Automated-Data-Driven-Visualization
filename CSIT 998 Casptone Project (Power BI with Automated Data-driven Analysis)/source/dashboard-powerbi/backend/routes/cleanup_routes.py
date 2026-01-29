"""
Cleanup routes for uploads directory.

- Stats, dry-run preview, and execution endpoints
- Intended for admin use only in production
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from utils.shared import UPLOAD_DIR
from utils.file_cleanup import (
    get_cleanup_stats,
    cleanup_old_files,
    cleanup_by_size_limit,
    scheduled_cleanup,
)

router = APIRouter(prefix="/api/cleanup", tags=["cleanup"])


class CleanupConfig(BaseModel):
    """Configuration for cleanup operation.
    
    Attributes:
        max_age_hours: Delete files older than this (default: 24)
        max_size_mb: Delete oldest files if directory exceeds this (default: 500)
        dry_run: If True, only preview without deleting
    """
    max_age_hours: Optional[float] = 24
    max_size_mb: Optional[float] = 500
    dry_run: bool = False


@router.get('/stats')
def get_upload_stats():
    """Get current statistics about upload directory.
    
    Returns file counts, sizes, and age distribution to help admins
    understand storage usage and decide when to run cleanup.
    
    Returns:
        JSON with:
        - total_files: Number of files in uploads
        - total_size_mb: Total storage used
        - oldest_file_age_hours: Age of oldest file
        - files_over_24h: Files older than 24 hours
        - files_over_7d: Files older than 7 days
        
    Example Response:
        {
            "ok": true,
            "stats": {
                "total_files": 45,
                "total_size_mb": 123.45,
                "oldest_file_age_hours": 72.5,
                "files_over_24h": 12,
                "files_over_7d": 3
            }
        }
    """
    try:
        stats = get_cleanup_stats(UPLOAD_DIR)
        return {
            "ok": True,
            "stats": stats,
            "directory": str(UPLOAD_DIR),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/preview')
def preview_cleanup(config: CleanupConfig):
    """Preview what files would be deleted without actually deleting.
    
    Dry-run mode to show admins what cleanup would do before committing.
    Useful for validating cleanup configuration.
    
    Args:
        config: Cleanup configuration with dry_run=True
        
    Returns:
        Statistics about files that would be deleted
        
    Example:
        POST /api/cleanup/preview
        {
            "max_age_hours": 48,
            "max_size_mb": 300,
            "dry_run": true
        }
    """
    if not config.dry_run:
        config.dry_run = True  # Force dry run for preview endpoint
    
    try:
        # Get current stats
        stats_before = get_cleanup_stats(UPLOAD_DIR)
        
        # Run dry-run cleanup
        age_deleted, age_kept, age_freed = cleanup_old_files(
            UPLOAD_DIR,
            max_age_hours=config.max_age_hours or 24,
            dry_run=True
        )
        
        size_deleted, size_freed = cleanup_by_size_limit(
            UPLOAD_DIR,
            max_size_mb=config.max_size_mb or 500,
            dry_run=True
        )
        
        return {
            "ok": True,
            "preview": True,
            "current_stats": stats_before,
            "would_delete": {
                "by_age": age_deleted,
                "by_size": size_deleted,
                "total": age_deleted + size_deleted,
            },
            "would_free_mb": round(age_freed + size_freed, 2),
            "would_keep": age_kept,
            "config": {
                "max_age_hours": config.max_age_hours,
                "max_size_mb": config.max_size_mb,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/run')
def run_cleanup(config: CleanupConfig):
    """Execute file cleanup operation.
    
    Actually deletes files based on configuration. This is a destructive
    operation and should only be accessible to admins.
    
    Args:
        config: Cleanup configuration
        
    Returns:
        Results of cleanup operation including files deleted and space freed
        
    Warning:
        This permanently deletes files. Recommend running /preview first.
        
    Example:
        POST /api/cleanup/run
        {
            "max_age_hours": 24,
            "max_size_mb": 500
        }
    """
    if config.dry_run:
        return {
            "ok": False,
            "error": "Use /api/cleanup/preview for dry-run operations"
        }
    
    try:
        result = scheduled_cleanup(
            UPLOAD_DIR,
            max_age_hours=config.max_age_hours or 24,
            max_size_mb=config.max_size_mb or 500
        )
        
        return {
            "ok": True,
            "result": result,
            "message": f"Cleaned up {result['total_deleted']} files, freed {result['total_freed_mb']} MB"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete('/all')
def clear_all_uploads():
    """Delete ALL files in uploads directory (DANGEROUS).
    
    Emergency cleanup option that removes all uploaded files.
    Should only be used in development or after confirming all imports are complete.
    
    Warning:
        This is irreversible. All temporary upload files will be deleted.
        Active import sessions may fail if their files are deleted.
        
    Returns:
        Count of files deleted
    """
    try:
        deleted_count = 0
        freed_size = 0
        
        for filepath in UPLOAD_DIR.iterdir():
            if filepath.is_file() and filepath.name != '.gitkeep':
                size = filepath.stat().st_size
                filepath.unlink()
                deleted_count += 1
                freed_size += size
        
        return {
            "ok": True,
            "deleted": deleted_count,
            "freed_mb": round(freed_size / (1024 * 1024), 2),
            "warning": "All upload files have been deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

