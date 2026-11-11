"""
main.py
FastAPI backend for NeuroPredict Alzheimer's Risk Assessment.
Loads the trained CatBoost pipeline (final_catboost_top5.pkl) and serves assessment,
key factor weights, and 4-page A4 PDF report generation endpoints.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from report_generator import create_pdf_report

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
MODEL_PATH = BASE_DIR / "final_catboost_top5.pkl"
REPORTS_DIR = BASE_DIR / "reports"

os.makedirs(REPORTS_DIR, exist_ok=True)

# App initialization
app = FastAPI(
    title="NeuroPredict Assessment API",
    description="Production API powering the NeuroPredict Alzheimer's Assessment platform.",
    version="2.1.0"
)

# -------------------------------------------------------------------
# Production-Ready CORS Configuration
# -------------------------------------------------------------------
# Configurable via environment variable ALLOWED_ORIGINS (comma-separated)
custom_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in custom_origins_env.split(",") if o.strip()]

# Default local development origins
default_origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5500",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000"
]

for d in default_origins:
    if d not in allowed_origins:
        allowed_origins.append(d)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.github\.io", # Seamlessly allows GitHub Pages deployments
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Model Loading & Compatibility
# -------------------------------------------------------------------
model = None
key_factors_cache = None

FEATURE_COLUMNS = [
    "Functional_Assessment_Score",
    "MMSE_Score",
    "ADL_Score",
    "Memory_Complaints",
    "Behavioral_Problems"
]

FEATURE_DISPLAY_NAMES = {
    "Functional_Assessment_Score": "Functional Assessment",
    "MMSE_Score": "MMSE Score",
    "ADL_Score": "ADL Score",
    "Memory_Complaints": "Memory Complaints",
    "Behavioral_Problems": "Behavioral Problems"
}


def load_model():
    """Load model with cross-version scikit-learn unpickling resilience."""
    global model, key_factors_cache

    if not MODEL_PATH.exists():
        fallback = BASE_DIR / "model" / "final_catboost_top5.pkl"
        if fallback.exists():
            target_path = fallback
        else:
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
    else:
        target_path = MODEL_PATH

    print(f"Loading assessment model from {target_path}...")
    loaded_model = joblib.load(target_path)

    # Patch SimpleImputer for scikit-learn version compatibility
    if hasattr(loaded_model, "named_steps") and "preprocessing" in loaded_model.named_steps:
        for name, step, cols in loaded_model.named_steps["preprocessing"].transformers_:
            if hasattr(step, "named_steps"):
                for sname, s in step.named_steps.items():
                    if hasattr(s, "_fit_dtype") and not hasattr(s, "_fill_dtype"):
                        s._fill_dtype = s._fit_dtype

    model = loaded_model

    # Pre-extract factor relevance weights
    try:
        cb = model.named_steps["model"]
        raw_importances = cb.get_feature_importance()
        factors_list = []
        for col, imp in zip(FEATURE_COLUMNS, raw_importances):
            factors_list.append({
                "factor": FEATURE_DISPLAY_NAMES[col],
                "raw_name": col,
                "weight": round(float(imp), 1)
            })
        factors_list.sort(key=lambda x: x["weight"], reverse=True)
        for rank, item in enumerate(factors_list, 1):
            item["rank"] = rank
        key_factors_cache = factors_list
    except Exception as e:
        print(f"Notice: Could not pre-compute factor weights: {e}")

    print("Assessment engine loaded successfully.")


# Load model at startup
load_model()


# -------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------
class PatientInput(BaseModel):
    Functional_Assessment_Score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Functional Assessment Score (0 to 10)"
    )
    MMSE_Score: float = Field(
        ...,
        ge=0.0,
        le=30.0,
        description="MMSE Score (0 to 30)"
    )
    ADL_Score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="ADL Score (0 to 10)"
    )
    Memory_Complaints: int = Field(
        ...,
        ge=0,
        le=1,
        description="Memory Complaints (0 for No, 1 for Yes)"
    )
    Behavioral_Problems: int = Field(
        ...,
        ge=0,
        le=1,
        description="Behavioral Problems (0 for No, 1 for Yes)"
    )

    @field_validator("Functional_Assessment_Score")
    @classmethod
    def validate_fas(cls, v):
        if not (0.0 <= v <= 10.0):
            raise ValueError("Functional Assessment Score must be between 0 and 10")
        return round(float(v), 1)

    @field_validator("MMSE_Score")
    @classmethod
    def validate_mmse(cls, v):
        if not (0.0 <= v <= 30.0):
            raise ValueError("MMSE Score must be between 0 and 30")
        return round(float(v), 0)

    @field_validator("ADL_Score")
    @classmethod
    def validate_adl(cls, v):
        if not (0.0 <= v <= 10.0):
            raise ValueError("ADL Score must be between 0 and 10")
        return round(float(v), 1)

    @field_validator("Memory_Complaints", "Behavioral_Problems")
    @classmethod
    def validate_binary(cls, v):
        if v not in (0, 1):
            raise ValueError("Field must be 0 (No) or 1 (Yes)")
        return int(v)


# -------------------------------------------------------------------
# Helper Guidance & Meaning Generators (Plain Language)
# -------------------------------------------------------------------
def get_factor_meaning(name: str, value: float) -> str:
    """Return user-friendly plain-language meaning for entered values."""
    if name == "Functional Assessment":
        if value >= 8.0:
            return "Good daily independence"
        elif value >= 6.0:
            return "Moderate daily independence"
        else:
            return "Difficulty with daily independence"
    elif name == "MMSE Score":
        if value >= 24.0:
            return "Normal cognitive range"
        elif value >= 19.0:
            return "Needs attention"
        else:
            return "Concerning cognitive score"
    elif name == "ADL Score":
        if value >= 8.0:
            return "Independent daily activities"
        elif value >= 6.0:
            return "Some difficulty"
        else:
            return "Needs assistance with daily activities"
    elif name == "Memory Complaints":
        return "Reported" if int(value) == 1 else "None reported"
    elif name == "Behavioral Problems":
        return "Observed" if int(value) == 1 else "None observed"
    return "Assessed"


def generate_helpful_guidance(data: Dict[str, Any]) -> List[str]:
    """Generates practical, supportive suggestions based strictly on entered values."""
    guidance = []

    mmse = data.get("MMSE_Score", 30)
    memory = data.get("Memory_Complaints", 0)
    behavior = data.get("Behavioral_Problems", 0)
    fas = data.get("Functional_Assessment_Score", 10)
    adl = data.get("ADL_Score", 10)

    if memory == 1:
        guidance.append(
            "Keep track of changes in memory and discuss persistent concerns with a qualified healthcare professional."
        )

    if behavior == 1:
        guidance.append(
            "Monitor noticeable changes in mood or behavior and discuss persistent or worsening changes with a healthcare professional."
        )

    if fas < 6.0 or adl < 6.0:
        guidance.append(
            "Consider discussing difficulties with everyday activities with a healthcare professional."
        )

    if mmse < 24.0:
        guidance.append(
            "Consider discussing memory or cognitive concerns with a qualified healthcare professional."
        )

    if len(guidance) == 0:
        guidance.append(
            "Maintain regular physical activity and gentle aerobic exercise to support overall health."
        )
        guidance.append(
            "Maintain a consistent and restful sleep routine."
        )
        guidance.append(
            "Stay socially engaged with family, friends, and community activities."
        )
        guidance.append(
            "Follow a balanced, nutritious diet and stay well hydrated."
        )
        guidance.append(
            "Keep regular periodic health checkups with your doctor."
        )

    return guidance


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------
@app.get("/health")
def health_check():
    """
    Health check endpoint:
    Returns 'status: online' to allow frontend to check backend connectivity.
    """
    return {
        "status": "online",
        "service": "NeuroPredict Assessment API"
    }


@app.get("/feature-importance")
def get_key_factors():
    """Returns the key factors evaluated by the assessment system."""
    if key_factors_cache is None:
        raise HTTPException(status_code=500, detail="Key factors unavailable")

    return {
        "factors": [item["factor"] for item in key_factors_cache],
        "weights": [item["weight"] for item in key_factors_cache],
        "detailed": key_factors_cache
    }


@app.post("/predict")
def evaluate_assessment(patient: PatientInput):
    """
    Assessment evaluation endpoint:
    Receives JSON containing the five patient features, evaluates with the assessment system,
    and returns friendly, non-technical results and guidance.
    """
    if model is None:
        raise HTTPException(status_code=500, detail="Assessment system is temporarily unavailable.")

    try:
        patient_dict = {
            "Functional_Assessment_Score": patient.Functional_Assessment_Score,
            "MMSE_Score": patient.MMSE_Score,
            "ADL_Score": patient.ADL_Score,
            "Memory_Complaints": patient.Memory_Complaints,
            "Behavioral_Problems": patient.Behavioral_Problems
        }
        df = pd.DataFrame([patient_dict])

        # Run evaluation
        prediction_val = int(model.predict(df)[0])
        probabilities = model.predict_proba(df)[0]
        prob_no_ad = round(float(probabilities[0]) * 100, 1)
        prob_ad = round(float(probabilities[1]) * 100, 1)

        is_higher_risk = (prob_ad >= 50.0 or prediction_val == 1)
        risk_level = "Higher Risk" if is_higher_risk else "Lower Risk"
        risk_color = "#ef4444" if is_higher_risk else "#10b981"

        if is_higher_risk:
            result_headline = "Higher Risk"
            explanation = (
                "Based on the information provided, the assessment indicates a higher level of risk. "
                "This result is based on the information entered in the assessment. It is intended for "
                "educational and research purposes and should not be treated as a medical diagnosis."
            )
        else:
            result_headline = "Lower Risk"
            explanation = (
                "Based on the information provided, the assessment indicates a lower level of risk. "
                "This result is based on the information entered in the assessment. It is intended for "
                "educational and research purposes and should not be treated as a medical diagnosis."
            )

        patient_scores = {
            "functional": {
                "name": "Functional Assessment",
                "value": patient.Functional_Assessment_Score,
                "max": 10.0,
                "display": f"{patient.Functional_Assessment_Score} / 10",
                "percent": round((patient.Functional_Assessment_Score / 10.0) * 100, 1),
                "meaning": get_factor_meaning("Functional Assessment", patient.Functional_Assessment_Score)
            },
            "mmse": {
                "name": "MMSE Score",
                "value": patient.MMSE_Score,
                "max": 30.0,
                "display": f"{int(patient.MMSE_Score)} / 30",
                "percent": round((patient.MMSE_Score / 30.0) * 100, 1),
                "meaning": get_factor_meaning("MMSE Score", patient.MMSE_Score)
            },
            "adl": {
                "name": "ADL Score",
                "value": patient.ADL_Score,
                "max": 10.0,
                "display": f"{patient.ADL_Score} / 10",
                "percent": round((patient.ADL_Score / 10.0) * 100, 1),
                "meaning": get_factor_meaning("ADL Score", patient.ADL_Score)
            },
            "memory": {
                "name": "Memory Complaints",
                "value": patient.Memory_Complaints,
                "display": "Yes" if patient.Memory_Complaints == 1 else "No",
                "meaning": get_factor_meaning("Memory Complaints", patient.Memory_Complaints)
            },
            "behavior": {
                "name": "Behavioral Problems",
                "value": patient.Behavioral_Problems,
                "display": "Yes" if patient.Behavioral_Problems == 1 else "No",
                "meaning": get_factor_meaning("Behavioral Problems", patient.Behavioral_Problems)
            }
        }

        factors_table = [
            {
                "factor": "Functional Assessment",
                "value": f"{patient.Functional_Assessment_Score} / 10",
                "meaning": patient_scores["functional"]["meaning"]
            },
            {
                "factor": "MMSE Score",
                "value": f"{int(patient.MMSE_Score)} / 30",
                "meaning": patient_scores["mmse"]["meaning"]
            },
            {
                "factor": "ADL Score",
                "value": f"{patient.ADL_Score} / 10",
                "meaning": patient_scores["adl"]["meaning"]
            },
            {
                "factor": "Memory Complaints",
                "value": "Yes" if patient.Memory_Complaints == 1 else "No",
                "meaning": patient_scores["memory"]["meaning"]
            },
            {
                "factor": "Behavioral Problems",
                "value": "Yes" if patient.Behavioral_Problems == 1 else "No",
                "meaning": patient_scores["behavior"]["meaning"]
            }
        ]

        top_factors = [item["factor"] for item in key_factors_cache[:3]]
        top_factors_str = f"{top_factors[0]}, {top_factors[1]} and {top_factors[2]}"

        summary = (
            f"Based on the information provided, the assessment indicates a {risk_level.lower()} level of risk. "
            f"The estimated Alzheimer's likelihood was {prob_ad}%. "
            f"The strongest factors in this assessment were {top_factors_str}."
        )

        guidance = generate_helpful_guidance(patient_dict)
        general_wellness = [
            "Maintain regular physical activity and gentle aerobic exercise.",
            "Maintain a consistent and restorative sleep routine.",
            "Stay socially engaged with family, friends, and community.",
            "Follow a balanced, wholesome diet and stay well hydrated.",
            "Keep regular periodic health checkups with your doctor.",
            "Keep track of noticeable changes in memory, mood, or daily routines over time."
        ]

        assessment_id = f"NP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        timestamp_formatted = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        return {
            "prediction": prediction_val,
            "probability_no_alzheimers": prob_no_ad,
            "probability_alzheimers": prob_ad,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "result_headline": result_headline,
            "alzheimers_likelihood": prob_ad,
            "other_likelihood": prob_no_ad,
            "explanation": explanation,
            "summary": summary,
            "patient_scores": patient_scores,
            "factors_table": factors_table,
            "key_factors": key_factors_cache,
            "helpful_guidance": guidance,
            "general_wellness": general_wellness,
            "assessment_id": assessment_id,
            "timestamp_formatted": timestamp_formatted,
            "important_notice": (
                "This application provides an assessment based on the information entered and is intended "
                "for educational and research purposes. It is not a medical diagnosis and should not replace "
                "evaluation by a qualified healthcare professional."
            )
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to process assessment: {str(e)}"
        )


predict = evaluate_assessment


@app.post("/download-report")
def download_pdf_report(report_data: Dict[str, Any]):
    """Generates a professional 4-page A4 PDF report and returns it as a download."""
    try:
        assessment_id = report_data.get("assessment_id", f"NP-{uuid.uuid4().hex[:6].upper()}")
        pdf_filename = f"NeuroPredict_Assessment_Report_{assessment_id}.pdf"
        output_path = REPORTS_DIR / pdf_filename

        pdf_bytes = create_pdf_report(report_data, str(output_path))

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{pdf_filename}"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

