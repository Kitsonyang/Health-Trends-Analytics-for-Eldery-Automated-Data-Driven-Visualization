"""
Temporary File Cleanup Utility

Manages automatic cleanup of temporary upload files to prevent disk space bloat.
Import preview generates temporary CSV files that should be deleted after processing
or after a retention period.

Features:
- Age-based cleanup (default: 24 hours)
- Size-based cleanup (when directory exceeds threshold)
- Manual cleanup API endpoint
- Scheduled background cleanup (optional)

Design Rationale:
- Temporary files are only needed during import preview/commit flow
- After successful commit or user abandonment, files can be safely deleted
- Prevents disk space issues in production environments
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def get_file_age_hours(filepath: Path) -> float:
    """Calculate file age in hours.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Age of file in hours
    """
    try:
        mtime = os.path.getmtime(filepath)
        age_seconds = time.time() - mtime
        return age_seconds / 3600
    except Exception as e:
        logger.error(f"Error getting file age for {filepath}: {e}")
        return 0


def get_directory_size_mb(directory: Path) -> float:
    """Calculate total size of directory in MB.
    
    Args:
        directory: Path to directory
        
    Returns:
        Total size in megabytes
    """
    total_size = 0
    try:
        for entry in directory.rglob('*'):
            if entry.is_file():
                total_size += entry.stat().st_size
    except Exception as e:
        logger.error(f"Error calculating directory size: {e}")
    
    return total_size / (1024 * 1024)


def cleanup_old_files(
    directory: Path,
    max_age_hours: float = 24,
    dry_run: bool = False
) -> Tuple[int, int, float]:
    """Remove files older than specified age.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum file age in hours (default: 24)
        dry_run: If True, only report what would be deleted without deleting
        
    Returns:
        Tuple of (files_deleted, files_kept, space_freed_mb)
        
    Example:
        # Clean files older than 24 hours
        deleted, kept, freed = cleanup_old_files(UPLOAD_DIR, max_age_hours=24)
        print(f"Deleted {deleted} files, freed {freed:.2f} MB")
    """
    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return 0, 0, 0.0
    
    files_deleted = 0
    files_kept = 0
    space_freed = 0.0
    
    try:
        for filepath in directory.iterdir():
            if not filepath.is_file():
                continue
            
            # Skip .gitkeep files
            if filepath.name == '.gitkeep':
                files_kept += 1
                continue
            
            age_hours = get_file_age_hours(filepath)
            
            if age_hours > max_age_hours:
                file_size = filepath.stat().st_size
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would delete: {filepath.name} (age: {age_hours:.1f}h, size: {file_size / 1024:.1f} KB)")
                else:
                    try:
                        filepath.unlink()
                        files_deleted += 1
                        space_freed += file_size
                        logger.info(f"Deleted: {filepath.name} (age: {age_hours:.1f}h)")
                    except Exception as e:
                        logger.error(f"Failed to delete {filepath}: {e}")
                        files_kept += 1
            else:
                files_kept += 1
    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    
    space_freed_mb = space_freed / (1024 * 1024)
    
    if not dry_run:
        logger.info(f"Cleanup complete: deleted {files_deleted} files, kept {files_kept} files, freed {space_freed_mb:.2f} MB")
    
    return files_deleted, files_kept, space_freed_mb


def cleanup_by_size_limit(
    directory: Path,
    max_size_mb: float = 500,
    dry_run: bool = False
) -> Tuple[int, float]:
    """Remove oldest files if directory exceeds size limit.
    
    Args:
        directory: Directory to clean
        max_size_mb: Maximum directory size in MB (default: 500 MB)
        dry_run: If True, only report what would be deleted
        
    Returns:
        Tuple of (files_deleted, space_freed_mb)
        
    Strategy:
        Delete oldest files first until directory size is below limit
    """
    current_size = get_directory_size_mb(directory)
    
    if current_size <= max_size_mb:
        logger.info(f"Directory size ({current_size:.2f} MB) is within limit ({max_size_mb} MB)")
        return 0, 0.0
    
    # Get all files sorted by modification time (oldest first)
    files = []
    for filepath in directory.iterdir():
        if filepath.is_file() and filepath.name != '.gitkeep':
            files.append((filepath, filepath.stat().st_mtime, filepath.stat().st_size))
    
    files.sort(key=lambda x: x[1])  # Sort by mtime
    
    files_deleted = 0
    space_freed = 0.0
    
    for filepath, mtime, size in files:
        if current_size - (space_freed / (1024 * 1024)) <= max_size_mb:
            break
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete: {filepath.name} (size: {size / 1024:.1f} KB)")
        else:
            try:
                filepath.unlink()
                files_deleted += 1
                space_freed += size
                logger.info(f"Deleted (size limit): {filepath.name}")
            except Exception as e:
                logger.error(f"Failed to delete {filepath}: {e}")
    
    space_freed_mb = space_freed / (1024 * 1024)
    
    if not dry_run:
        logger.info(f"Size-based cleanup: deleted {files_deleted} files, freed {space_freed_mb:.2f} MB")
    
    return files_deleted, space_freed_mb


def get_cleanup_stats(directory: Path) -> dict:
    """Get statistics about files in directory.
    
    Args:
        directory: Directory to analyze
        
    Returns:
        Dictionary with cleanup statistics
    """
    if not directory.exists():
        return {
            'total_files': 0,
            'total_size_mb': 0,
            'oldest_file_age_hours': 0,
            'files_over_24h': 0,
            'files_over_7d': 0,
        }
    
    total_files = 0
    total_size = 0
    oldest_age = 0
    files_over_24h = 0
    files_over_7d = 0
    
    for filepath in directory.iterdir():
        if not filepath.is_file() or filepath.name == '.gitkeep':
            continue
        
        total_files += 1
        total_size += filepath.stat().st_size
        
        age_hours = get_file_age_hours(filepath)
        oldest_age = max(oldest_age, age_hours)
        
        if age_hours > 24:
            files_over_24h += 1
        if age_hours > 24 * 7:
            files_over_7d += 1
    
    return {
        'total_files': total_files,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'oldest_file_age_hours': round(oldest_age, 2),
        'files_over_24h': files_over_24h,
        'files_over_7d': files_over_7d,
    }


def scheduled_cleanup(
    directory: Path,
    max_age_hours: float = 24,
    max_size_mb: float = 500
) -> dict:
    """Run scheduled cleanup (combines age and size strategies).
    
    This function is designed to be called by a cron job or background scheduler.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum file age in hours
        max_size_mb: Maximum directory size in MB
        
    Returns:
        Dictionary with cleanup results
    """
    logger.info(f"Starting scheduled cleanup for {directory}")
    
    # Get stats before cleanup
    stats_before = get_cleanup_stats(directory)
    
    # Run age-based cleanup
    age_deleted, age_kept, age_freed = cleanup_old_files(directory, max_age_hours)
    
    # Run size-based cleanup if needed
    size_deleted, size_freed = cleanup_by_size_limit(directory, max_size_mb)
    
    # Get stats after cleanup
    stats_after = get_cleanup_stats(directory)
    
    result = {
        'timestamp': datetime.now().isoformat(),
        'before': stats_before,
        'after': stats_after,
        'age_cleanup': {
            'files_deleted': age_deleted,
            'files_kept': age_kept,
            'space_freed_mb': round(age_freed, 2),
        },
        'size_cleanup': {
            'files_deleted': size_deleted,
            'space_freed_mb': round(size_freed, 2),
        },
        'total_deleted': age_deleted + size_deleted,
        'total_freed_mb': round(age_freed + size_freed, 2),
    }
    
    logger.info(f"Scheduled cleanup complete: {result}")
    
    return result

