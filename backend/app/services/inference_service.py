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
from backend.app.services.model_loader import (
    resolve_and_load_model,
    LoadedModelBundle,
    clear_model_cache,
)

CANONICAL_TO_MODEL_FEATURE = {
    "air_temperature": "Air temperature [K]",
    "process_temperature": "Process temperature [K]",
    "rotational_speed": "Rotational speed [rpm]",
    "torque": "Torque [Nm]",
    "tool_wear": "Tool wear [min]",
    "product_type": "Type"
}

PRODUCTION_MODEL_PATHS = {
    "WITH_TYPE": settings.BASE_DIR / "ml" / "artifacts" / "models" / "production_m2_config_a.joblib",
    "NO_TYPE": settings.BASE_DIR / "ml" / "artifacts" / "models" / "production_m2_config_b.joblib",
}

# Alias for backwards compatibility with tests and callers
MODEL_PATHS = PRODUCTION_MODEL_PATHS


def execute_analysis(
    db: Session,
    org_id: str,
    compatibility_check_id: str,
    job_id: Optional[str] = None,
    commit: bool = True
) -> AnalysisResult:
    """
    Executes failure prediction analysis for an authorized compatibility check (AC-FP-1..8, AC-AP-1..5).
    """
    # Prevent duplicate AnalysisResult records if job was retried or previously finished
    if job_id:
        existing_res = db.query(AnalysisResult).filter(
            AnalysisResult.job_id == job_id,
            AnalysisResult.organisation_id == org_id
        ).first()
        if existing_res:
            return existing_res

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
                # Normalise L/M/H so e.g. "l " or "m" is not silently one-hot encoded as unknown
                input_df[model_col_name] = df_raw[col_name].astype(str).str.strip().str.upper()
            else:
                unit_declared = spec.get("unit", "K" if "temperature" in canon_name else "rpm" if "speed" in canon_name else "Nm" if "torque" in canon_name else "min")
                canon_unit = "K" if "temperature" in canon_name else "rpm" if "speed" in canon_name else "Nm" if "torque" in canon_name else "min"
                input_df[model_col_name] = convert_to_canonical(df_raw[col_name], unit_declared, canon_unit)

    # 3. Load trained model bundle via registry-driven loader
    cfg = profile.configuration
    loaded_bundle = resolve_and_load_model(db, profile)
    pipeline = loaded_bundle.pipeline
    calibrator = loaded_bundle.calibrator
    tau = loaded_bundle.optimal_threshold
    model_path = loaded_bundle.artifact_path
    is_production_bundle = True

    # 4. Predict probabilities (using calibrated probabilities when available)
    if calibrator is not None:
        probabilities = calibrator.predict_proba(input_df)[:, 1]
    else:
        probabilities = pipeline.predict_proba(input_df)[:, 1]
        probabilities = pipeline.predict_proba(input_df)[:, 1]

    # 5. Determine threshold and assign risk classes
    risk_classes = []
    predicted_failures = 0
    medium_threshold = 0.5 * tau if is_production_bundle else 0.20
    for p in probabilities:
        if p >= tau:
            risk_classes.append("HIGH")
            predicted_failures += 1
        elif p >= medium_threshold:
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
        "threshold_type": "EMPIRICAL_OPTIMAL" if is_production_bundle else "PROVISIONAL",
        "threshold_note": (
            f"Calibrated operational decision threshold ({tau*100:.1f}%) optimized for predictive maintenance inspection prioritization."
            if is_production_bundle else
            "Operational decision threshold optimized for equipment inspection prioritization."
        ),
        "risk_distribution": {
            "LOW": int((np.array(risk_classes) == "LOW").sum()),
            "MEDIUM": int((np.array(risk_classes) == "MEDIUM").sum()),
            "HIGH": int((np.array(risk_classes) == "HIGH").sum())
        }
    }

    # 8. Top rows (top 20 highest probabilities) with TreeSHAP attributions
    top_indices = np.argsort(probabilities)[::-1][:20]
    
    # Compute TreeSHAP attributions for top rows if tree model available
    shap_matrix = None
    feature_names_out: List[str] = []
    explanation_meta = None
    try:
        classifier_step = None
        preprocessor_step = None
        if hasattr(pipeline, "named_steps"):
            classifier_step = pipeline.named_steps.get("classifier")
            preprocessor_step = pipeline.named_steps.get("preprocessor")

        if classifier_step is not None and preprocessor_step is not None and len(top_indices) > 0:
            import shap
            X_top = input_df.iloc[top_indices]
            X_top_trans = preprocessor_step.transform(X_top)
            explainer = shap.TreeExplainer(classifier_step)
            shap_matrix = explainer.shap_values(X_top_trans)
            base_val = float(explainer.expected_value)
            raw_margin = classifier_step.predict(X_top_trans, output_margin=True)
            reconstructed = np.sum(shap_matrix, axis=1) + base_val
            max_delta = float(np.max(np.abs(reconstructed - raw_margin)))
            feature_names_out = list(preprocessor_step.get_feature_names_out())
            explanation_meta = {
                "method": "FactorAttribution",
                "base_margin_value": round(base_val, 5),
                "additivity_verified": bool(max_delta <= 1e-5),
                "max_reconstruction_delta": round(max_delta, 8),
                "non_causality_disclaimer": "Contributing factors describe statistical model associations, not physical causation.",
                "optimal_threshold": tau,
            }
    except Exception as e:
        explanation_meta = {
            "method": "FeatureImportance",
            "error": str(e),
            "non_causality_disclaimer": "Feature attributions describe model behaviour, not physical causation."
        }

    top_rows = []
    for i, idx in enumerate(top_indices):
        features = {}
        for k in input_df.columns:
            val = input_df[k].iloc[idx]
            if isinstance(val, (int, float, np.number)):
                # NaN is not valid JSON (PostgreSQL JSON columns reject it) -> store null
                features[k] = None if pd.isna(val) else float(val)
            else:
                features[k] = str(val)
        row_obj = {
            "row_index": int(idx),
            "failure_probability": round(float(probabilities[idx]), 4),
            "risk_class": risk_classes[idx],
            "ood_warning": bool(is_ood_array[idx]),
            "features": features
        }
        if shap_matrix is not None and i < len(shap_matrix):
            row_obj["feature_attributions"] = {
                fn: round(float(val), 5)
                for fn, val in zip(feature_names_out, shap_matrix[i])
            }
        top_rows.append(row_obj)

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

    # Provenance metadata
    summary["provenance"] = {
        "model_version": loaded_bundle.model_version,
        "model_version_id": loaded_bundle.model_version_id,
        "artifact_sha256": loaded_bundle.artifact_sha256,
        "configuration": loaded_bundle.configuration,
        "training_domain": "REFERENCE_DATASET",
        "calibration_method": "Platt Scaling (Logistic Sigmoid)",
        "decision_threshold": tau,
        "cost_ratio": round(loaded_bundle.cost_fn / loaded_bundle.cost_fp, 2),
        "model_card_reference": f"docs/model_cards/ai4i_failure_clf_{'typed' if 'WITH_TYPE' in loaded_bundle.configuration else 'notype'}.md"
    }

    # Create immutable AnalysisResult
    result = AnalysisResult(
        organisation_id=org_id,
        machine_id=check.machine_id,
        dataset_version_id=check.dataset_version_id,
        job_id=job_id,
        compatibility_check_id=check.id,
        profile_uuid=profile.id,
        configuration=cfg,
        model_version_id=loaded_bundle.model_version_id,
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
        artifact_uri=str(loaded_bundle.artifact_path),
        explanation_meta=explanation_meta,
        limitations=[
            "Model trained on AI4I 2020 synthetic reference dataset; probability calibration applied to ensure realistic failure estimates."
            if is_production_bundle else
            "Model trained on AI4I 2020 synthetic reference dataset.",
            "Predictions are advisory model scores, not physical failure frequencies of customer equipment.",
            f"Operational decision threshold ({tau*100:.1f}%) optimized to prioritize potential equipment failures over false alarms (cost-sensitive balance)."
            if is_production_bundle else
            "Operational decision threshold set to prioritize potential equipment failure inspection.",
            "Contributing factors describe statistical model associations, not physical causation."
        ],
        created_at=datetime.utcnow()
    )
    db.add(result)
    # autoflush is disabled; flush so result.id is populated before it is referenced below
    db.flush()

    # Usage event (PRD line 2601)
    db.add(UsageEvent(
        organisation_id=org_id,
        event_type="ANALYSIS_EXECUTION",
        quantity=1,
        details={"result_id": result.id, "rows": total_rows, "configuration": cfg}
    ))

    if commit:
        db.commit()
        db.refresh(result)
    else:
        db.flush()

    return result
