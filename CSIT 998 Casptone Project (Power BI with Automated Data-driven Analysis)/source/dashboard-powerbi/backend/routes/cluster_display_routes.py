"""
Serve and lazily render cluster visualizations.

- Heatmap, cluster sizes, demographics charts
- Lazy render with file cache; optional refresh parameter
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from utils.shared import (
    HEATMAP_PATH, SIZES_PATH, DEMOS_PATH,
    DISPLAY_RENDER_LOCK,
    ensure_models_loaded,
)
from services import cluster_service as cluster_display
from services import cluster_usage

router = APIRouter()


def _render_if_missing(path, fn, *args, **kwargs):
    """Lazy render chart with double-checked locking pattern.
    
    Ensures thread-safe chart generation with minimal lock contention.
    Only renders if file doesn't exist, preventing redundant computation.
    
    Args:
        path: Target file path for rendered chart
        fn: Rendering function to call
        *args, **kwargs: Arguments to pass to rendering function
    
    Raises:
        HTTPException: 500 if rendering fails after lock acquisition
    
    Note:
        Uses double-checked locking: checks existence before and after
        acquiring lock to avoid unnecessary blocking when file exists.
    """
    if not path.exists():
        with DISPLAY_RENDER_LOCK:
            if not path.exists():
                fn(*args, **kwargs)
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Failed to render {path.name}")


@router.get("/cluster/display/heatmap.png")
def get_heatmap(refresh: bool = Query(False)):
    """Serve cluster condition heatmap visualization.
    
    Generates or retrieves cached heatmap showing condition prevalence
    across patient clusters. Each cell shows how prevalent a specific
    condition is within a cluster (darker = more common).
    
    Args:
        refresh: If True, regenerate chart even if cached version exists
    
    Returns:
        FileResponse: PNG image of the heatmap
    
    Raises:
        HTTPException: 500 if ML models fail to load or rendering fails
    
    Note:
        - First request triggers matplotlib rendering (slow)
        - Subsequent requests serve cached PNG (fast)
        - Use refresh=true to regenerate after data import
    """
    ensure_models_loaded()
    if refresh and HEATMAP_PATH.exists():
        try:
            HEATMAP_PATH.unlink()
        except Exception:
            pass
    _render_if_missing(
        HEATMAP_PATH,
        cluster_display.show_cluster_heatmap,
        getattr(cluster_usage, "cluster_interpretations", {}) or {}
    )
    return FileResponse(HEATMAP_PATH, media_type="image/png")


@router.get("/cluster/display/cluster_sizes.png")
def get_cluster_sizes(refresh: bool = Query(False)):
    """Serve cluster size distribution bar chart.
    
    Shows patient count per cluster, useful for understanding cluster
    balance and identifying dominant patient groups.
    
    Args:
        refresh: If True, regenerate chart even if cached version exists
    
    Returns:
        FileResponse: PNG image of the bar chart
    
    Raises:
        HTTPException: 500 if ML models fail to load or rendering fails
    
    Note:
        Chart updates when new patients are clustered via ML endpoint.
        Use refresh=true after importing new patient data.
    """
    ensure_models_loaded()
    if refresh and SIZES_PATH.exists():
        try:
            SIZES_PATH.unlink()
        except Exception:
            pass
    _render_if_missing(
        SIZES_PATH,
        cluster_display.show_cluster_sizes,
        getattr(cluster_usage, "cluster_interpretations", {}) or {}
    )
    return FileResponse(SIZES_PATH, media_type="image/png")


@router.get("/cluster/display/demographics.png")
def get_demographics(refresh: bool = Query(False)):
    """Serve cluster demographic breakdown visualization.
    
    Displays age and gender distribution within each cluster,
    helping identify demographic patterns in patient segmentation.
    
    Args:
        refresh: If True, regenerate chart even if cached version exists
    
    Returns:
        FileResponse: PNG image of demographics chart
    
    Raises:
        HTTPException: 500 if ML models fail to load or rendering fails
    
    Use Case:
        Identify if certain clusters skew toward specific age groups
        or genders, informing targeted care strategies.
    """
    ensure_models_loaded()
    if refresh and DEMOS_PATH.exists():
        try:
            DEMOS_PATH.unlink()
        except Exception:
            pass
    _render_if_missing(
        DEMOS_PATH,
        cluster_display.show_demographics,
        getattr(cluster_usage, "cluster_interpretations", {}) or {}
    )
    return FileResponse(DEMOS_PATH, media_type="image/png")


