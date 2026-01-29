"""
Risk prediction endpoints (batch).

- Uses ML predictor; returns risk scores and categories
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Any, Dict, List
import numpy as np
from utils.shared import predictor
from pydantic import BaseModel

router = APIRouter()


class PatientInput(BaseModel):
    """Patient data input for risk prediction.
    
    Attributes:
        name: Patient identifier (not used in prediction, for tracking only)
        age: Patient age in years (used as model feature)
        gender: Patient gender ('Male'/'Female', encoded for model)
        conditions_dict: Dictionary of condition/symptom flags
            Keys are condition names (e.g., 'RF_Diabetes', 'RF_Hypertension')
            Values are binary indicators (0/1) or confidence scores (0.0-1.0)
    
    Note:
        conditions_dict keys must match feature names used during model training.
        Missing features will be imputed with zeros by the predictor.
    """
    name: str
    age: int
    gender: str
    conditions_dict: Dict[str, Any]


@router.post("/risk/predict")
async def predict_risk_batch(patients: List[PatientInput]):
    """Summary: Batch risk prediction.
    Returns: list of results per patient"""
    try:
        results = []
        for patient in patients:
            result = predictor.predict_patient_risk(
                age=patient.age,
                gender=patient.gender,
                patient_conditions=patient.conditions_dict,
                include_details=False
            )
            results.append(result)

        # Convert NumPy types to JSON-serializable format
        safe = jsonable_encoder(
            results,
            custom_encoder={
                np.integer: int,
                np.floating: float,
                np.ndarray: lambda v: v.tolist(),
            },
        )
        return JSONResponse(content=safe)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {e}")


