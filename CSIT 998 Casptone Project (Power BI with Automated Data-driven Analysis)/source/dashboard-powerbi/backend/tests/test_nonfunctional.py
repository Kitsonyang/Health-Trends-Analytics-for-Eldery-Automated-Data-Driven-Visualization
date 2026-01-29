import time
import pytest
from fastapi import status
import json
from starlette import status
def _mount_all(app):
    """Mounts all key routers for global checks."""
    from conftest import mount_router
    # Mount every router for full API coverage
    routers = [
        "routes.health_routes",
        "routes.data_routes",
        "routes.categories_routes",
        "routes.import_routes",
    ]
    for r in routers:
        mount_router(app, r)
    return app
# 1  Robustness and Error Handling
def test_invalid_route_returns_404(client, app):
    """Backend should return 404 for non-existent routes."""
    _mount_all(app)
    r = client.get("/api/thisdoesnotexist")
    assert r.status_code == status.HTTP_404_NOT_FOUND
def test_invalid_input_returns_400(client, app):
    """Backend should return 400 for bad input."""
    _mount_all(app)
    r = client.post("/api/categories", json={"category": "  "})
    assert r.status_code == 400
def test_import_commit_validates_mode(client, app):
    _mount_all(app)
    bad = client.post("/api/import/commit", json={"token": "x.csv", "mode": "bad"})
    assert bad.status_code == 400
# 2  Availability and Basic Uptime
def test_health_route_always_available(client, app):
    """Health endpoint should always return 200 and 'ok'."""
    _mount_all(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.json()
    assert j.get("status") == "ok"
# 3 Content-Type correctness
def test_content_type_is_json(client, app):
    _mount_all(app)
    for ep in ["/api/health", "/api/data/stats"]:
        r = client.get(ep)
        assert r.status_code == 200
        assert r.headers.get("Content-Type", "").startswith("application/json")
        # Parsable JSON
        json.loads(r.text)
#4 Method not allowed → 404/405  
@pytest.mark.parametrize("endpoint, method", [
    ("/api/health", "DELETE"),
    ("/api/data/stats", "POST"),  
    ("/api/categories", "PUT"),    
    ("/api/import/preview", "GET"),  
])
def test_method_not_allowed_or_404(client, app, endpoint, method):
    _mount_all(app)
    # Dynamically call the HTTP method
    response = getattr(client, method.lower())(endpoint)
    assert response.status_code in {
        status.HTTP_405_METHOD_NOT_ALLOWED,
        status.HTTP_404_NOT_FOUND
    }, f"Endpoint {endpoint} accepted {method}, expected 404/405 but got {response.status_code}"