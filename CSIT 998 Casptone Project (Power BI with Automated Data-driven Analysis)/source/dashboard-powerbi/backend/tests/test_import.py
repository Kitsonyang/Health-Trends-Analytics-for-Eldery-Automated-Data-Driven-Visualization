import io

CSV = (
    "PersonID,Start date,End date,M-Risk Factors,Gender,Age,MNA,BMI,Weight\n"
    "1,2020-01-01,2020-02-01,pain,male,60,12,22,70\n"
    "2,2020-03-01,2020-03-10,constipation,female,82,13,21,55\n"
)

def _mount(app):
    from conftest import mount_router
    mount_router(app, "routes.import_routes")

def test_import_preview_and_commit(client, app):
    _mount(app)
    files = {'file': ('data.csv', io.BytesIO(CSV.encode('utf-8')), 'text/csv')}
    prev = client.post("/api/import/preview", files=files)
    assert prev.status_code == 200
    token = prev.json()["token"]
    com = client.post("/api/import/commit", json={"token": token, "mode": "append"})
    assert com.status_code == 200 and com.json()["inserted"] == 2


