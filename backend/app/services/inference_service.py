"""
Inference and Analysis Execution Service (PRD v1.2 §8.6, §10.1, §13.5, AC-FP-1..8)
Loads trained models, executes unit-converted inference, tracks OOD rows,
computes calibrated failure probabilities and risk classes, and stores immutable AnalysisResult.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import joblib
from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.app.config import settings
from backend.app.models.dataset import DatasetVersion, ColumnMapping
from backend.app.models.compatibility import CompatibilityCheck, PipelineProfile
from backend.app.models.model import ModelVersion
from backend.app.models.analysis import AnalysisResult
from backend.app.models.usage import UsageEvent
from backend.app.services.compatibility_service import convert_to_canonical

CANONICAL_TO_MODEL_FEATURE = {
    "air_temperature": "Air temperature [K]",
    "process_temperature": "Process temperature [K]",
    "rotational_speed": "Rotational speed [rpm]",
    "torque": "Torque [Nm]",
    "tool_wear": "Tool wear [min]",
    "product_type": "Type"
}

MODEL_PATHS = {
    "NO_TYPE": settings.BASE_DIR / "ml/artifacts/models/EXP-008_xgboost_config_b.joblib",
    "WITH_TYPE": settings.BASE_DIR / "ml/artifacts/models/EXP-004_xgboost_config_a.joblib"
}

def execute_analysis(
    db: Session,
    org_id: str,
    compatibility_check_id: str,
    job_id: Optional[str] = None
) -> AnalysisResult:
    """
    Executes failure prediction analysis for an authorized compatibility check (AC-FP-1..8, AC-AP-1..5).
    """
    check = db.query(CompatibilityCheck).filter(
        CompatibilityCheck.id == compatibility_check_id,
        CompatibilityCheck.organisation_id == org_id
    ).first()
    if not check:
        raise HTTPException(status_code=404, detail="Compatibility check not found.")

    profile = check.profile
    dv = db.query(DatasetVersion).filter(DatasetVersion.id == check.dataset_version_id).first()
    mapping_record = db.query(ColumnMapping).filter(ColumnMapping.id == check.mapping_id).first()

    if not dv or not mapping_record:
        raise HTTPException(status_code=422, detail="Missing dataset version or column mapping.")

    # 1. Load dataset CSV
    storage_abs_path = settings.STORAGE_DIR / dv.storage_key
    if not storage_abs_path.exists():
        raise HTTPException(status_code=500, detail="Underlying dataset file missing from storage.")

    df_raw = pd.read_csv(storage_abs_path)
    total_rows = len(df_raw)

    # 2. Extract and convert canonical features
    input_df = pd.DataFrame()
    for canon_name, model_col_name in CANONICAL_TO_MODEL_FEATURE.items():
        if canon_name in mapping_record.mappings:
            spec = mapping_record.mappings[canon_name]
            col_name = spec["column"]
            if canon_name == "product_type":
                input_df[model_col_name] = df_raw[col_name].astype(str)
            else:
                unit_declared = spec.get("unit", "K" if "temperature" in canon_name else "rpm" if "speed" in canon_name else "Nm" if "torque" in canon_name else "min")
                canon_unit = "K" if "temperature" in canon_name else "rpm" if "speed" in canon_name else "Nm" if "torque" in canon_name else "min"
                input_df[model_col_name] = convert_to_canonical(df_raw[col_name], unit_declared, canon_unit)

    # 3. Load trained model pipeline
    cfg = profile.configuration
    model_path = MODEL_PATHS.get(cfg)
    if not model_path or not model_path.exists():
        raise HTTPException(status_code=500, detail=f"Model artifact not found for configuration '{cfg}'.")

    model_pipeline = joblib.load(model_path)

    # 4. Predict probabilities
    probabilities = model_pipeline.predict_proba(input_df)[:, 1]

    # 5. Determine threshold and assign risk classes
    # Provisional operational threshold based on asymmetric cost ratio C_FN/C_FP = 50 baseline.
    # Note: Empirical threshold tuning will be conducted under Stage 3 inner cross-validation.
    tau = 0.45  # provisional operational threshold
    risk_classes = []
    predicted_failures = 0
    for p in probabilities:
        if p >= tau:
            risk_classes.append("HIGH")
            predicted_failures += 1
        elif p >= 0.20:
            risk_classes.append("MEDIUM")
        else:
            risk_classes.append("LOW")

    # 6. Flag OOD rows
    ref_ranges = profile.document.get("reference_ranges", {})
    m = profile.document.get("applicability", {}).get("margin_fraction", 0.10)
    is_ood_array = np.zeros(total_rows, dtype=bool)

    for canon_name, model_col_name in CANONICAL_TO_MODEL_FEATURE.items():
        if canon_name in ref_ranges and model_col_name in input_df.columns:
            r_min = ref_ranges[canon_name]["min"]
            r_max = ref_ranges[canon_name]["max"]
            r_range = ref_ranges[canon_name]["range"]
            lower = r_min - m * r_range
            upper = r_max + m * r_range
            feat_ood = (input_df[model_col_name] < lower) | (input_df[model_col_name] > upper)
            is_ood_array = is_ood_array | feat_ood.to_numpy()

    ood_count = int(is_ood_array.sum())
    ood_fraction = round(ood_count / total_rows, 4) if total_rows > 0 else 0.0

    # 7. Summary statistics
    summary = {
        "total_rows": total_rows,
        "predicted_failures": predicted_failures,
        "failure_rate": round(predicted_failures / total_rows, 4) if total_rows > 0 else 0.0,
        "mean_failure_probability": round(float(np.mean(probabilities)), 4),
        "max_failure_probability": round(float(np.max(probabilities)), 4),
        "threshold_used": tau,
        "threshold_type": "PROVISIONAL",
        "threshold_note": "Provisional operational threshold (cost ratio C_FN/C_FP=50 baseline). Final empirical threshold will be tuned via Stage 3 inner cross-validation.",
        "risk_distribution": {
            "LOW": int((np.array(risk_classes) == "LOW").sum()),
            "MEDIUM": int((np.array(risk_classes) == "MEDIUM").sum()),
            "HIGH": int((np.array(risk_classes) == "HIGH").sum())
        }
    }

    # 8. Top rows (top 20 highest probabilities)
    top_indices = np.argsort(probabilities)[::-1][:20]
    top_rows = []
    for idx in top_indices:
        row_dict = {
            "row_index": int(idx),
            "failure_probability": round(float(probabilities[idx]), 4),
            "risk_class": risk_classes[idx],
            "ood_warning": bool(is_ood_array[idx]),
            "features": {k: float(input_df[k].iloc[idx]) if isinstance(input_df[k].iloc[idx], (int, float, np.number)) else str(input_df[k].iloc[idx]) for k in input_df.columns}
        }
        top_rows.append(row_dict)

    # 9. Result versioning
    latest_res = db.query(AnalysisResult).filter(
        AnalysisResult.machine_id == check.machine_id,
        AnalysisResult.dataset_version_id == check.dataset_version_id,
        AnalysisResult.profile_uuid == profile.id
    ).order_by(AnalysisResult.result_version.desc()).first()

    result_version = (latest_res.result_version + 1) if latest_res else 1

    # Flip previous is_latest to False
    db.query(AnalysisResult).filter(
        AnalysisResult.machine_id == check.machine_id,
        AnalysisResult.dataset_version_id == check.dataset_version_id,
        AnalysisResult.profile_uuid == profile.id
    ).update({"is_latest": False})

    # Fetch corresponding registered model
    model_record = db.query(ModelVersion).filter(
        ModelVersion.profile_uuid == profile.id,
        ModelVersion.stage == "PRODUCTION"
    ).first()

    # Create immutable AnalysisResult
    result = AnalysisResult(
        organisation_id=org_id,
        machine_id=check.machine_id,
        dataset_version_id=check.dataset_version_id,
        job_id=job_id,
        compatibility_check_id=check.id,
        profile_uuid=profile.id,
        configuration=cfg,
        model_version_id=model_record.id if model_record else None,
        pipeline="A",
        result_version=result_version,
        is_latest=True,
        training_domain="REFERENCE_DATASET",
        applicability_level=check.applicability_level,
        reliability_tier="REFERENCE_ONLY",
        ood_summary={
            "total_rows": total_rows,
            "flagged_rows": ood_count,
            "flagged_fraction": ood_fraction,
            "per_feature": check.applicability_detail.get("per_feature", {})
        },
        summary=summary,
        top_rows=top_rows,
        artifact_uri=str(model_path),
        limitations=[
            "Model trained on AI4I 2020 synthetic reference dataset; formal post-hoc calibration was not applied to baseline weights.",
            "Predictions are advisory model scores, not physical failure frequencies of customer equipment.",
            "Operational threshold (tau = 0.45) is a provisional baseline setting based on the asymmetric cost ratio C_FN/C_FP = 50; empirical threshold optimization is scheduled for the Stage 3 nested evaluation protocol.",
            "Feature attributions describe model behaviour, not physical causation."
        ],
        created_at=datetime.utcnow()
    )
    db.add(result)

    # Usage event (PRD line 2601)
    db.add(UsageEvent(
        organisation_id=org_id,
        event_type="ANALYSIS_EXECUTION",
        quantity=1,
        details={"result_id": result.id, "rows": total_rows, "configuration": cfg}
    ))

    db.commit()
    db.refresh(result)
    return result
