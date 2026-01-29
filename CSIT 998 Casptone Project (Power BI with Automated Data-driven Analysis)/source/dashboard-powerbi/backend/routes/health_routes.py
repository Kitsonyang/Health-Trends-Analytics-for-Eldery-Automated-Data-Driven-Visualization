"""
Health and readiness endpoints.

- /api/health: liveness
- /healthz: readiness (ensures ML models loaded)
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from utils.shared import ensure_models_loaded

router = APIRouter()


@router.get('/api/health')
def api_health():
    """Summary: Liveness check.
    Returns: {status: "ok"}"""
    return {"status": "ok"}


@router.get('/healthz')
def healthz():
    """Summary: Readiness check (ensures ML models load).
    Returns: {ok} or {ok: False, error}"""
    try:
        ensure_models_loaded()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


