def _mount(app):
    from conftest import mount_router
    mount_router(app, "routes.categories_routes")

def test_list_and_create_category(client, app):
    _mount(app)
    r = client.get("/api/categories")
    assert r.status_code == 200 and r.json()["ok"] is True
    r2 = client.post("/api/categories", json={"category": "Respiratory"})
    data = r2.json()
    assert r2.status_code == 200 and data["ok"] is True
    assert data["item"]["category"] == "Respiratory" 
    assert data["item"]["id"] > 0 

def test_create_validation(client, app):
    _mount(app)
    r = client.post("/api/categories", json={"category": "  "})
    assert r.status_code == 400
    assert "category must not be empty" in r.text

def test_delete(client, app):
    _mount(app)
    de = client.delete("/api/categories/1")
    assert de.status_code == 200 and de.json()["deleted_category_id"] == 1
