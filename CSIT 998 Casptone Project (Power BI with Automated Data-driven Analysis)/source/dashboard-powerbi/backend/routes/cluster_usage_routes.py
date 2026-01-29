"""
ML clustering/classification endpoints.

- SVD for dimensionality reduction, K-Means for clustering
- Returns cluster id/label, confidence, and reduced features
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from typing import Any, Dict, List
import numpy as np
from pydantic import BaseModel

from services import cluster_usage
from utils.shared import ensure_models_loaded, predictor
from fastapi.encoders import jsonable_encoder

router = APIRouter()


class PatientPayload(BaseModel):
    """Request payload for patient clustering prediction.
    
    Attributes:
        patient_id: Optional patient identifier for tracking (not used in model)
        features: Dict of symptom/condition features
            Keys should match rf_columns feature names
            Values are typically binary (0/1) or continuous scores
    
    Example:
        {
            "patient_id": "P001",
            "features": {
                "RF_Diabetes": 1,
                "RF_Hypertension": 1,
                "RF_Age": 75
            }
        }
    """
    patient_id: str | None = None
    features: Dict[str, Any]


@router.post("/cluster/usage/predict")
async def predict_cluster(payload: PatientPayload):
    """Predict patient cluster; returns id/label/confidence/features."""
    ensure_models_loaded()
    patient_id = getattr(payload, 'patient_id', None) or "Unknown"
    features = getattr(payload, 'features', None) or {}
    try:
        result = cluster_usage.classify_patient(
            patient_data=features,
            svd_model=cluster_usage.svd_model,
            clustering_model=cluster_usage.clustering_model,
            rf_columns=cluster_usage.rf_columns,
            cluster_interpretations=getattr(cluster_usage, "cluster_interpretations", {}) or {},
            patient_id=patient_id,
        )
        # Convert NumPy types to JSON-serializable format
        safe = jsonable_encoder(
            result,
            custom_encoder={
                np.integer: int,
                np.floating: float,
                np.ndarray: lambda v: v.tolist(),
            },
        )
        return JSONResponse(content=safe)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Classification failed: {e}")


@router.get("/cluster/usage/rf-columns")
def rf_columns():
    """Summary: Get required feature names.
    Returns: {rf_columns[]}"""
    ensure_models_loaded()
    return {"rf_columns": cluster_usage.rf_columns or []}


