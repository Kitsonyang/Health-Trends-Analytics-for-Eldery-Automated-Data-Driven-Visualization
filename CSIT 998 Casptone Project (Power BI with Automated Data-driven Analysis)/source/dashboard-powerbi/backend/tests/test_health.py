def test_api_health(client, app):
    from conftest import mount_router
    mount_router(app, "routes.health_routes")
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
