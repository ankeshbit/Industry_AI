"""
Compatibility, Applicability, and Reliability Engine (PRD v1.2 §8.4, §13.5, AC-CE-1..7, AC-AP-1..5)
The single authoritative component that evaluates dataset compatibility,
reference-domain applicability, and authorizes execution jobs.
"""

import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.config import settings
from backend.app.models.machine import Machine
from backend.app.models.dataset import Dataset, DatasetVersion, ColumnMapping, ValidationReport
from backend.app.models.compatibility import (
    PipelineProfile, CompatibilityCheck, WarningAcknowledgement, LimitationAcknowledgement
)

# Standard unit conversion multipliers to canonical units (PRD v1.2 §8.4.1)
def convert_to_canonical(values: pd.Series, unit_declared: str, canonical_unit: str) -> pd.Series:
    """Converts a series of values from declared unit to canonical profile unit."""
    if unit_declared == canonical_unit:
        return values.astype(float)

    if canonical_unit == "K":
        if unit_declared == "degC":
            return values.astype(float) + 273.15
        elif unit_declared == "degF":
            return (values.astype(float) - 32.0) * (5.0 / 9.0) + 273.15
    elif canonical_unit == "rpm":
        if unit_declared == "rad_s":
            return values.astype(float) * (60.0 / (2.0 * np.pi))
        elif unit_declared == "Hz":
            return values.astype(float) * 60.0
    elif canonical_unit == "Nm":
        if unit_declared == "lbf_ft":
            return values.astype(float) * 1.355818
    elif canonical_unit == "min":
        if unit_declared == "h":
            return values.astype(float) * 60.0

    return values.astype(float)

def evaluate_compatibility(
    db: Session,
    org_id: str,
    dataset_version_id: str,
    profile_id: str,
    mapping_id: Optional[str] = None
) -> CompatibilityCheck:
    """
    Executes the 3-stage Compatibility, Applicability, and Reliability evaluation (PRD v1.2 §8.4).
    Stores an immutable CompatibilityCheck record.
    """
    # 1. Fetch resources
    dv = db.query(DatasetVersion).filter(
        DatasetVersion.id == dataset_version_id,
        DatasetVersion.organisation_id == org_id
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    dataset = dv.dataset
    machine = dataset.machine
    profile = db.query(PipelineProfile).filter(PipelineProfile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Pipeline profile not found.")

    doc = profile.document
    required_features = doc.get("required_features", [])
    allowed_formats = doc.get("allowed_formats", ["csv"])
    eligible_categories = doc.get("machine_categories", [])
    eligible_dataset_types = doc.get("dataset_types", [])

    # Fetch mapping
    if mapping_id:
        mapping_record = db.query(ColumnMapping).filter(
            ColumnMapping.id == mapping_id,
            ColumnMapping.organisation_id == org_id,
            ColumnMapping.dataset_version_id == dataset_version_id
        ).first()
        if not mapping_record:
            raise HTTPException(status_code=404, detail="Column mapping not found.")
    else:
        mapping_record = db.query(ColumnMapping).filter(
            ColumnMapping.dataset_version_id == dataset_version_id,
            ColumnMapping.profile_id == profile_id
        ).order_by(ColumnMapping.mapping_version.desc()).first()

        # Fallback to any existing mapping on this dataset version to evaluate shared features
        if not mapping_record:
            mapping_record = db.query(ColumnMapping).filter(
                ColumnMapping.dataset_version_id == dataset_version_id
            ).order_by(ColumnMapping.mapping_version.desc()).first()

    reasons: List[Dict[str, Any]] = []
    status_code = "COMPATIBLE"

    # =========================================================================
    # STAGE 1: DATASET COMPATIBILITY (PRD v1.2 §8.4.2)
    # =========================================================================

    # 1. Format Gate
    if dv.file_kind.lower() not in allowed_formats:
        status_code = "UNSUPPORTED_FORMAT"
        reasons.append({
            "code": "UNSUPPORTED_FORMAT",
            "severity": "ERROR",
            "observed": dv.file_kind,
            "expected": allowed_formats,
            "message": f"File format '{dv.file_kind}' is not supported by profile '{profile_id}'.",
            "remedy": f"Upload dataset in one of: {allowed_formats}"
        })

    # 2. Category & Dataset Type Gate
    if machine.category_code not in eligible_categories:
        status_code = "INCOMPATIBLE"
        reasons.append({
            "code": "E_CATEGORY",
            "severity": "ERROR",
            "observed": machine.category_code,
            "expected": eligible_categories,
            "message": f"Machine category '{machine.category_code}' is not eligible for this profile.",
            "remedy": "Select a profile that supports this machine category."
        })

    if dataset.dataset_type not in eligible_dataset_types:
        status_code = "INCOMPATIBLE"
        reasons.append({
            "code": "E_DATASET_TYPE",
            "severity": "ERROR",
            "observed": dataset.dataset_type,
            "expected": eligible_dataset_types,
            "message": f"Dataset type '{dataset.dataset_type}' does not match profile requirement.",
            "remedy": f"Confirm dataset type as one of: {eligible_dataset_types}"
        })

    # 3. Schema Gate
    if not mapping_record or not mapping_record.mappings:
        status_code = "INCOMPATIBLE"
        reasons.append({
            "code": "E_MISSING_MAPPING",
            "severity": "ERROR",
            "message": "No column mapping exists for this profile.",
            "remedy": "Complete the column mapping wizard before running analysis."
        })
    else:
        mapped_dict = mapping_record.mappings
        for req_feat in required_features:
            fname = req_feat["name"]
            if fname not in mapped_dict:
                status_code = "INCOMPATIBLE"
                reasons.append({
                    "code": "E_MISSING_FEATURE",
                    "severity": "ERROR",
                    "feature": fname,
                    "expected": req_feat.get("allowed_units", req_feat.get("allowed_values")),
                    "message": f"Required feature '{fname}' is not mapped.",
                    "remedy": f"Map a dataset column to canonical feature '{fname}' in the onboarding wizard."
                })
            else:
                mapping_spec = mapped_dict[fname]
                col_name = mapping_spec.get("column")
                # Verify column exists in dataset version
                existing_cols = [c.name for c in dv.columns]
                col_meta = {c.name: c for c in dv.columns}
                if col_name in col_meta and req_feat.get("kind") != "categorical" and col_meta[col_name].inferred_type != "numeric":
                    # Previously this crashed later in convert_to_canonical (astype(float)) with a 500
                    status_code = "INCOMPATIBLE"
                    reasons.append({
                        "code": "E_NON_NUMERIC_COLUMN",
                        "severity": "ERROR",
                        "feature": fname,
                        "observed": col_meta[col_name].inferred_type,
                        "expected": "numeric",
                        "message": f"Column '{col_name}' mapped to '{fname}' is not numeric.",
                        "remedy": "Clean the column (remove text/units from cells) or map a numeric column."
                    })
                if col_name in col_meta and req_feat.get("kind") == "categorical" and req_feat.get("allowed_values"):
                    allowed = {str(v).strip().upper() for v in req_feat["allowed_values"]}
                    stats = col_meta[col_name].stats or {}
                    observed = {str(v).strip().upper() for v in stats.get("sample_values", [])}
                    if stats.get("unique_count", 0) > len(allowed) or not observed <= allowed:
                        status_code = "INCOMPATIBLE"
                        reasons.append({
                            "code": "E_INVALID_CATEGORY_VALUES",
                            "severity": "ERROR",
                            "feature": fname,
                            "observed": sorted(observed),
                            "expected": sorted(allowed),
                            "message": f"Column '{col_name}' mapped to '{fname}' contains values outside {sorted(allowed)}.",
                            "remedy": "Map a column whose values are exactly the AI4I quality variants L/M/H."
                        })
                if col_name not in existing_cols:
                    status_code = "INCOMPATIBLE"
                    reasons.append({
                        "code": "E_UNKNOWN_COLUMN",
                        "severity": "ERROR",
                        "feature": fname,
                        "observed": col_name,
                        "message": f"Mapped column '{col_name}' does not exist in dataset version.",
                        "remedy": "Re-map canonical features to existing columns."
                    })

        # Check special product_type rules
        if "product_type" in mapped_dict and profile.configuration == "WITH_TYPE":
            reasons.append({
                "code": "W_TYPE_SEMANTICS_ASSERTED",
                "severity": "WARNING",
                "message": "User asserted that column represents AI4I-style quality variant semantics (L/M/H).",
                "remedy": "Verify product type meanings correspond to manufacturing variants."
            })

    # 4. Quantity Gate
    if dv.row_count is not None and dv.row_count < 1:
        status_code = "INSUFFICIENT_DATA"
        reasons.append({
            "code": "E_EMPTY_DATASET",
            "severity": "ERROR",
            "observed": dv.row_count,
            "expected": ">= 1 row",
            "message": "Dataset contains 0 rows.",
            "remedy": "Upload a dataset containing valid observation rows."
        })

    # Required-feature completeness gate (profile minimums.required_feature_completeness, default 0.95).
    # It was declared in every profile but never enforced, so mostly-empty columns reached inference.
    min_completeness = (doc.get("minimums") or {}).get("required_feature_completeness", 0.0)
    if min_completeness and dv.row_count and mapping_record and mapping_record.mappings:
        stats_by_col = {c.name: (c.stats or {}) for c in dv.columns}
        for req_feat in required_features:
            spec = mapping_record.mappings.get(req_feat["name"])
            if not spec or spec.get("column") not in stats_by_col:
                continue
            nulls = stats_by_col[spec["column"]].get("null_count", 0)
            completeness = round(1.0 - nulls / dv.row_count, 4)
            if completeness < min_completeness:
                reasons.append({
                    "code": "E_INSUFFICIENT_COMPLETENESS",
                    "severity": "ERROR",
                    "feature": req_feat["name"],
                    "observed": completeness,
                    "expected": f">= {min_completeness}",
                    "message": f"Required feature '{req_feat['name']}' is only {round(completeness * 100, 1)}% populated.",
                    "remedy": "Fill or remove rows with missing values for this feature and re-upload."
                })

    # Status Precedence (PRD §8.4.2 line 989, AC-CE-2):
    # UNSUPPORTED_FORMAT > INCOMPATIBLE > INSUFFICIENT_DATA > COMPATIBLE_WITH_WARNINGS > COMPATIBLE
    has_unsupported = any(r["code"] == "UNSUPPORTED_FORMAT" for r in reasons)
    insufficient_codes = ("E_EMPTY_DATASET",)
    has_incompatible = any(
        r["severity"] == "ERROR"
        and r["code"] != "UNSUPPORTED_FORMAT"
        and "INSUFFICIENT" not in r["code"]
        and r["code"] not in insufficient_codes
        for r in reasons
    )
    has_insufficient = any("INSUFFICIENT" in r["code"] or r["code"] in insufficient_codes for r in reasons)
    has_warnings = any(r["severity"] == "WARNING" for r in reasons)

    if has_unsupported:
        status_code = "UNSUPPORTED_FORMAT"
    elif has_incompatible:
        status_code = "INCOMPATIBLE"
    elif has_insufficient:
        status_code = "INSUFFICIENT_DATA"
    elif has_warnings:
        status_code = "COMPATIBLE_WITH_WARNINGS"
    else:
        status_code = "COMPATIBLE"

    # =========================================================================
    # STAGE 2: MODEL APPLICABILITY ASSESSMENT (PRD v1.2 §8.4.4)
    # =========================================================================
    applicability_level = "NOT_ASSESSED"
    applicability_detail = {}

    if status_code in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS") and mapping_record:
        # Load dataset to evaluate reference-range coverage
        storage_abs_path = settings.STORAGE_DIR / dv.storage_key
        df = pd.read_csv(storage_abs_path)
        ref_ranges = doc.get("reference_ranges", {})
        m = doc.get("applicability", {}).get("margin_fraction", 0.10)
        warn_thresh = doc.get("applicability", {}).get("warn_row_fraction", 0.01)
        block_thresh = doc.get("applicability", {}).get("block_row_fraction", 0.30)

        total_rows = len(df)
        is_ood_row = np.zeros(total_rows, dtype=bool)
        per_feature_ood = {}

        for req_feat in required_features:
            fname = req_feat["name"]
            if req_feat.get("kind") == "categorical":
                continue
            if fname in ref_ranges and fname in mapping_record.mappings:
                col_name = mapping_record.mappings[fname]["column"]
                unit_declared = mapping_record.mappings[fname].get("unit", req_feat["unit_canonical"])
                canon_unit = req_feat["unit_canonical"]

                # Convert to canonical
                converted_series = convert_to_canonical(df[col_name], unit_declared, canon_unit)

                r_min = ref_ranges[fname]["min"]
                r_max = ref_ranges[fname]["max"]
                r_range = ref_ranges[fname]["range"]
                lower_bound = r_min - m * r_range
                upper_bound = r_max + m * r_range

                feat_ood_mask = (converted_series < lower_bound) | (converted_series > upper_bound)
                is_ood_row = is_ood_row | feat_ood_mask.to_numpy()
                ood_count = int(feat_ood_mask.sum())
                per_feature_ood[fname] = round(ood_count / total_rows, 4)

        flagged_fraction = round(float(is_ood_row.sum()) / total_rows, 4) if total_rows > 0 else 0.0

        if flagged_fraction > block_thresh:
            applicability_level = "MOSTLY_OUTSIDE_REFERENCE_RANGE"
            reasons.append({
                "code": "E_OOD_MAJORITY",
                "severity": "ERROR",
                "observed": f"{round(flagged_fraction * 100, 1)}% rows outside reference range",
                "expected": f"<= {round(block_thresh * 100, 1)}%",
                "message": "Most rows lie outside the model's reference range; results would be extrapolation.",
                "remedy": "Check units and scaling, or analyse a subset within the supported range."
            })
        elif flagged_fraction > warn_thresh:
            applicability_level = "PARTLY_OUTSIDE_REFERENCE_RANGE"
            reasons.append({
                "code": "W_OOD",
                "severity": "WARNING",
                "observed": f"{round(flagged_fraction * 100, 1)}% rows outside reference range",
                "message": "A fraction of rows lie outside the training reference distribution.",
                "remedy": "Acknowledge the out-of-distribution warning before running analysis."
            })
            if status_code == "COMPATIBLE":
                status_code = "COMPATIBLE_WITH_WARNINGS"
        else:
            applicability_level = "IN_REFERENCE_RANGE"

        applicability_detail = {
            "flagged_row_fraction": flagged_fraction,
            "per_feature": per_feature_ood,
            "thresholds": {"margin_fraction": m, "warn_fraction": warn_thresh, "block_fraction": block_thresh},
            "domain_note": "Model trained on AI4I 2020 synthetic data; your machine and operating conditions may differ.",
            "disclaimer": "This level is a warning mechanism, not evidence that predictions are reliable or unreliable."
        }

    # =========================================================================
    # STAGE 3: MODEL RELIABILITY TIER (PRD v1.2 §8.4.6, AC-AP-3)
    # =========================================================================
    reliability_tier = "REFERENCE_ONLY"
    reliability_basis = {
        "statement": "Reference-dataset-trained model; not validated on your equipment.",
        "training_domain": "REFERENCE_DATASET",
        "customer_validation_performed": False
    }

    # Compute inputs hash to track immutability and freshness
    raw_hash_input = f"{dv.id}:{mapping_record.id if mapping_record else 'none'}:{profile.id}:{status_code}"
    inputs_hash = hashlib.sha256(raw_hash_input.encode()).hexdigest()

    # Save CompatibilityCheck record
    check = CompatibilityCheck(
        organisation_id=org_id,
        dataset_version_id=dataset_version_id,
        machine_id=machine.id,
        mapping_id=mapping_record.id if mapping_record else None,
        profile_uuid=profile.id,
        status=status_code,
        reasons=reasons,
        applicability_level=applicability_level,
        applicability_detail=applicability_detail,
        reliability_tier=reliability_tier,
        reliability_basis=reliability_basis,
        inputs_hash=inputs_hash
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check

def verify_job_creation_gate(
    db: Session,
    org_id: str,
    compatibility_check_id: str,
    acknowledged_reason_codes: List[str],
    limitation_acknowledged: bool
) -> CompatibilityCheck:
    """
    Evaluates the Job-Creation Gate (PRD v1.2 §8.4.7, AC-CE-3..5, AC-AP-5).
    Raises corresponding 422 errors if any gate fails.
    """
    check = db.query(CompatibilityCheck).filter(
        CompatibilityCheck.id == compatibility_check_id,
        CompatibilityCheck.organisation_id == org_id
    ).first()
    if not check:
        raise HTTPException(status_code=404, detail="Compatibility check not found.")

    # 1. Stage 1 check
    if check.status in ("UNSUPPORTED_FORMAT", "INCOMPATIBLE", "INSUFFICIENT_DATA"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": check.status,
                    "message": f"Dataset is not compatible ({check.status}).",
                    "details": check.reasons
                }
            }
        )

    # 2. Stage 2 check
    if check.applicability_level == "MOSTLY_OUTSIDE_REFERENCE_RANGE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "APPLICABILITY_BLOCKED",
                    "message": "Most rows lie outside the model's reference range; results would be extrapolation.",
                    "details": check.reasons
                }
            }
        )

    # 3. Warning acknowledgements (AC-CE-4)
    active_warnings = [r["code"] for r in check.reasons if r.get("severity") == "WARNING"]
    missing_acks = [code for code in active_warnings if code not in acknowledged_reason_codes]
    if missing_acks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "WARNINGS_NOT_ACKNOWLEDGED",
                    "message": "Active compatibility and applicability warnings have not been acknowledged.",
                    "missing_codes": missing_acks
                }
            }
        )

    # 4. Limitation acknowledgement (AC-AP-5)
    if not limitation_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "LIMITATIONS_NOT_ACKNOWLEDGED",
                    "message": "Reference model limitation must be explicitly acknowledged.",
                    "statement": "This is a reference-dataset-trained model. It has not been validated on your equipment. Results are advisory."
                }
            }
        )

    return check
