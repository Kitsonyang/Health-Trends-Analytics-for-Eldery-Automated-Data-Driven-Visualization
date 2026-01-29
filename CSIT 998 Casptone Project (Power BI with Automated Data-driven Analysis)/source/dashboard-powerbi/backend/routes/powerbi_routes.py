"""
Power BI refresh and token endpoints.

- Trigger dataset refresh and poll status via REST API
- Service principal OAuth2; config via environment variables
"""

from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from typing import Any, Dict, Optional
import json
import time
from pydantic import BaseModel
import requests
from config import load_powerbi_config
from datetime import datetime, timezone


router = APIRouter()
@router.get('/api/powerbi/embed-url')
def powerbi_embed_url():
    """Summary: Get embed URL.
    Returns: {ok, url} or 404"""
    cfg = load_powerbi_config()
    url = getattr(cfg, 'embed_url', None)
    if not url or not isinstance(url, str) or not url.strip():
        raise HTTPException(status_code=404, detail='PBI_EMBED_URL not configured')
    return {"ok": True, "url": url.strip()}



# OAuth2 scope for Power BI API access
PBI_SCOPE_STR = "https://analysis.windows.net/powerbi/api/.default"


def _acquire_access_token() -> Dict[str, Any]:
    """Summary: Acquire OAuth2 token.
    Returns: {access_token, token_type, expires_in}"""
    cfg = load_powerbi_config()
    url = f"https://login.microsoftonline.com/{cfg.tenant_id}/oauth2/v2.0/token"
    
    # OAuth2 client credentials grant
    payload = {
        'client_id': cfg.client_id,
        'grant_type': 'client_credentials',
        'scope': PBI_SCOPE_STR,
        'client_secret': cfg.client_secret,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request token endpoint: {e}")
    try:
        result = res.json()
    except Exception:
        result = {"raw": res.text or res.reason}
    if not res.ok or 'access_token' not in result:
        detail = result if isinstance(result, dict) else {'error': 'token_request_failed'}
        raise HTTPException(status_code=res.status_code or 500, detail=detail)
    return result


@router.get('/api/powerbi/token')
def powerbi_token_preview():
    """Summary: Debug token preview.
    Returns: {ok, token_type, expires_in, token_preview, token}"""
    result = _acquire_access_token()
    token = result.get("access_token", "")
    print(f"token: {token}")
    preview = (token[:24] + "...") if token else ""
    return {
        "ok": True,
        "token_type": result.get("token_type"),
        "expires_in": result.get("expires_in"),
        "token_preview": preview,
        "token": token,
    }


class RefreshPayload(BaseModel):
    """Request body for triggering Power BI dataset refresh.
    
    Attributes:
        dataset_id: Target dataset ID (optional, defaults to PBI_DATASET_ID env)
        notify_option: Email notification setting
            - "MailOnFailure": Send email only if refresh fails
            - "NoNotification": Suppress all emails (default)
    """
    dataset_id: Optional[str] = None
    notify_option: Optional[str] = None


@router.post('/api/powerbi/datasets/refresh')
def powerbi_trigger_refresh(payload: RefreshPayload = Body(default=RefreshPayload())):
    """Summary: Trigger dataset refresh (async).
    Returns: {ok, dataset_id, status_code}"""
    cfg = load_powerbi_config()
    dataset_id = (payload.dataset_id or cfg.dataset_id or '').strip()
    if not dataset_id:
        raise HTTPException(status_code=400, detail='dataset_id is required (either in payload or PBI_DATASET_ID env)')

    token_result = _acquire_access_token()
    token = token_result.get("access_token")
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{cfg.workspace_id}/datasets/{dataset_id}/refreshes"

    body: Dict[str, Any] = {}
    if payload.notify_option:
        body["notifyOption"] = payload.notify_option

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    try:
        res = requests.post(url, headers=headers, json=body if body else None, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to call Power BI refresh API: {e}")

    ok = res.status_code == 202
    return {
        'ok': ok,
        'dataset_id': dataset_id,
        'status_code': res.status_code,
    }


@router.get('/api/powerbi/datasets/refresh/status')
def powerbi_refresh_status(dataset_id: Optional[str] = Query(default=None)):
    """Summary: Get refresh status/history.
    Returns: {ok, dataset_id, today_count, total, latest, history}"""
    cfg = load_powerbi_config()
    final_dataset_id = (dataset_id or cfg.dataset_id or '').strip()
    if not final_dataset_id:
        raise HTTPException(status_code=400, detail='dataset_id is required (either in query or PBI_DATASET_ID env)')

    token_result = _acquire_access_token()
    token = token_result.get("access_token")
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{cfg.workspace_id}/datasets/{final_dataset_id}/refreshes"

    headers = {
        'Authorization': f'Bearer {token}',
    }
    try:
        res = requests.get(url, headers=headers, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query Power BI refresh status: {e}")

    if not res.ok:
        try:
            detail = res.json()
        except Exception:
            detail = res.text
        raise HTTPException(status_code=res.status_code, detail=detail)

    data = res.json() or {}
    history = data.get('value') or []

    # Count today's refreshes based on UTC date of startTime
    today_utc = datetime.now(timezone.utc).date()
    def _parse_start_date(item: Dict[str, Any]) -> Optional[datetime]:
        """Parse ISO 8601 timestamp from Power BI API response."""
        ts = item.get('startTime')
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return None

    today_count = 0
    for item in history:
        dt = _parse_start_date(item)
        if dt and dt.date() == today_utc:
            today_count += 1

    latest = history[0] if history else None

    return {
        'ok': True,
        'dataset_id': final_dataset_id,
        'today_count': today_count,
        'total': len(history),
        'latest': latest,
        'history': history,
    }


@router.get('/api/powerbi/datasets/refresh/records')
def powerbi_refresh_records_raw(dataset_id: Optional[str] = Query(default=None)):
    """Summary: Get raw refresh history (debug).
    Returns: raw JSON from Power BI API"""
    cfg = load_powerbi_config()
    final_dataset_id = (dataset_id or cfg.dataset_id or '').strip()
    if not final_dataset_id:
        raise HTTPException(status_code=400, detail='dataset_id is required (either in query or PBI_DATASET_ID env)')

    token_result = _acquire_access_token()
    token = token_result.get("access_token")
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{cfg.workspace_id}/datasets/{final_dataset_id}/refreshes"

    headers = {
        'Authorization': f'Bearer {token}',
    }
    try:
        res = requests.get(url, headers=headers, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query Power BI refresh records: {e}")

    if not res.ok:
        try:
            detail = res.json()
        except Exception:
            detail = res.text
        raise HTTPException(status_code=res.status_code, detail=detail)

    return res.json()


@router.get('/api/powerbi/datasets/refresh/stream')
def powerbi_refresh_stream(dataset_id: Optional[str] = Query(default=None)):
    """Summary: SSE stream for refresh status.
    Returns: text/event-stream"""
    cfg = load_powerbi_config()
    final_dataset_id = (dataset_id or cfg.dataset_id or '').strip()
    if not final_dataset_id:
        raise HTTPException(status_code=400, detail='dataset_id is required (either in query or PBI_DATASET_ID env)')

    def _sse_event(event: str, data: Dict[str, Any]) -> str:
        return f"event: {event}\n" + f"data: {json.dumps(data)}\n\n"

    def event_generator():
        # initial event
        yield _sse_event('status', {'status': 'processing'})
        # poll status until terminal state or max attempts
        max_attempts = 60  # ~5 minutes with 5s interval
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            # Query latest status (reuse logic from /status)
            token_result = _acquire_access_token()
            token = token_result.get("access_token")
            url = f"https://api.powerbi.com/v1.0/myorg/groups/{cfg.workspace_id}/datasets/{final_dataset_id}/refreshes"
            headers = { 'Authorization': f'Bearer {token}' }
            try:
                res = requests.get(url, headers=headers, timeout=30)
                if not res.ok:
                    try:
                        detail = res.json()
                    except Exception:
                        detail = res.text
                    yield _sse_event('error', {'status': 'error', 'detail': detail})
                    break
                data = res.json() or {}
                history = data.get('value') or []
                latest = history[0] if history else None
                status = (latest or {}).get('status')
                if status == 'Completed':
                    yield _sse_event('status', {'status': 'completed', 'latest': latest})
                    break
                if status == 'Failed':
                    yield _sse_event('status', {'status': 'failed', 'latest': latest})
                    break
                # keep alive/progress tick
                yield _sse_event('status', {'status': 'processing'})
            except Exception as e:
                yield _sse_event('error', {'status': 'error', 'detail': str(e)})
                break
            time.sleep(5)
        else:
            # timeout
            yield _sse_event('status', {'status': 'timeout'})

    headers = {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    return StreamingResponse(event_generator(), media_type='text/event-stream', headers=headers)
