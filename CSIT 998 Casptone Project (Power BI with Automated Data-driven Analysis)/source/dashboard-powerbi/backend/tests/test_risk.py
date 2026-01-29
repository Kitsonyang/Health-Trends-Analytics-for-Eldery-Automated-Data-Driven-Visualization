import json
import pytest
from starlette import status
import importlib

def _mount(app):
    from conftest import mount_router
    mount_router(app, "routes.risk_routes")

def test_risk_predict_batch_ok(client, app):
    _mount(app)
    payload = [
        {
            "name": "Alice",
            "age": 60,
            "gender": "female",
            "conditions_dict": {"hypertension": True, "pain": True}
        },
        {
            "name": "Bob",
            "age": 45,
            "gender": "male",
            "conditions_dict": {}
        },
    ]
    r = client.post("/risk/predict", json=payload)
    assert r.status_code == status.HTTP_200_OK
    data = r.json()
    assert isinstance(data, list) and len(data) == 2
    # From the predictor stub in conftest: {"score": 0.42, "age": age, "gender": gender, "n_conds": len(conditions)}
    assert data[0]["age"] == 60
    assert data[0]["gender"] == "female"
    assert data[0]["n_conds"] == 2
    assert isinstance(data[0]["score"], (int, float))
    assert data[1]["age"] == 45
    assert data[1]["gender"] == "male"
    assert data[1]["n_conds"] == 0

def test_predict_risk_returns_500_on_predictor_error(client, app, monkeypatch):
    _mount(app)
    mod = importlib.import_module("routes.risk_routes")

    # Force an error from the predictor
    def boom(*args, **kwargs):
        raise RuntimeError("simulated predictor failure")
    monkeypatch.setattr(mod.predictor, "predict_patient_risk", boom)

    payload = [{"name": "Alice", "age": 60, "gender": "female", "conditions_dict": {"pain": True}}]
    r = client.post("/risk/predict", json=payload)

    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    body = (r.text or "").lower()
    # Error message comes from your except-block:
    assert "batch prediction failed:" in body
   