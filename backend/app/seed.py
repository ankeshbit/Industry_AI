"""
Database Seeding Module for INDUSTRIA AI (PRD v1.2 §8.2.2, §8.4.1, §10.1, §12.2)
Seeds machine categories, pipeline profiles, model artifacts, and evaluation baselines.
"""

import json
from sqlalchemy.orm import Session
from backend.app.models.machine import MachineCategory
from backend.app.models.compatibility import PipelineProfile
from backend.app.models.model import ModelVersion, ModelEvaluation

AI4I_REFERENCE_RANGES = {
    "air_temperature": {
        "min": 295.3,
        "max": 304.5,
        "range": 9.2,
        "mean": 300.0,
        "std": 2.0,
        "unit": "K"
    },
    "process_temperature": {
        "min": 305.7,
        "max": 313.8,
        "range": 8.1,
        "mean": 310.0,
        "std": 1.48,
        "unit": "K"
    },
    "rotational_speed": {
        "min": 1168.0,
        "max": 2886.0,
        "range": 1718.0,
        "mean": 1538.78,
        "std": 179.28,
        "unit": "rpm"
    },
    "torque": {
        "min": 3.8,
        "max": 76.6,
        "range": 72.8,
        "mean": 39.99,
        "std": 9.97,
        "unit": "Nm"
    },
    "tool_wear": {
        "min": 0.0,
        "max": 253.0,
        "range": 253.0,
        "mean": 107.95,
        "std": 63.65,
        "unit": "min"
    }
}

AI4I_NO_TYPE_DOC = {
    "profile_id": "ai4i_failure_no_type",
    "version": "1.0.0",
    "pipeline": "A",
    "configuration": "NO_TYPE",
    "objective": "FAILURE_PROBABILITY_CURRENT_STATE",
    "training_domain": "REFERENCE_DATASET",
    "machine_categories": ["GENERAL_MACHINE_TOOL"],
    "dataset_types": ["TABULAR_OPERATING_STATE"],
    "allowed_formats": ["csv", "xlsx", "parquet"],
    "required_features": [
        {"name": "air_temperature", "unit_canonical": "K", "allowed_units": ["K", "degC", "degF"], "kind": "numeric"},
        {"name": "process_temperature", "unit_canonical": "K", "allowed_units": ["K", "degC", "degF"], "kind": "numeric"},
        {"name": "rotational_speed", "unit_canonical": "rpm", "allowed_units": ["rpm", "rad_s", "Hz"], "kind": "numeric"},
        {"name": "torque", "unit_canonical": "Nm", "allowed_units": ["Nm", "lbf_ft"], "kind": "numeric"},
        {"name": "tool_wear", "unit_canonical": "min", "allowed_units": ["min", "h"], "kind": "numeric"}
    ],
    "optional_features": [],
    "forbidden_features": ["machine_failure", "TWF", "HDF", "PWF", "OSF", "RNF", "UDI", "product_id", "product_type"],
    "minimums": {"rows": 1, "required_feature_completeness": 0.95},
    "reference_ranges": AI4I_REFERENCE_RANGES,
    "applicability": {"margin_fraction": 0.10, "warn_row_fraction": 0.01, "block_row_fraction": 0.30},
    "preprocessing_recipe": "ai4i_features_no_type@1.0.0",
    "model_versions": ["ai4i_failure_clf_notype@Production"]
}

AI4I_WITH_TYPE_DOC = {
    "profile_id": "ai4i_failure_with_type",
    "version": "1.0.0",
    "pipeline": "A",
    "configuration": "WITH_TYPE",
    "objective": "FAILURE_PROBABILITY_CURRENT_STATE",
    "training_domain": "REFERENCE_DATASET",
    "machine_categories": ["GENERAL_MACHINE_TOOL"],
    "dataset_types": ["TABULAR_OPERATING_STATE"],
    "allowed_formats": ["csv", "xlsx", "parquet"],
    "required_features": [
        {"name": "air_temperature", "unit_canonical": "K", "allowed_units": ["K", "degC", "degF"], "kind": "numeric"},
        {"name": "process_temperature", "unit_canonical": "K", "allowed_units": ["K", "degC", "degF"], "kind": "numeric"},
        {"name": "rotational_speed", "unit_canonical": "rpm", "allowed_units": ["rpm", "rad_s", "Hz"], "kind": "numeric"},
        {"name": "torque", "unit_canonical": "Nm", "allowed_units": ["Nm", "lbf_ft"], "kind": "numeric"},
        {"name": "tool_wear", "unit_canonical": "min", "allowed_units": ["min", "h"], "kind": "numeric"},
        {"name": "product_type", "kind": "categorical", "allowed_values": ["L", "M", "H"], "ai4i_specific": True}
    ],
    "optional_features": [],
    "forbidden_features": ["machine_failure", "TWF", "HDF", "PWF", "OSF", "RNF", "UDI", "product_id"],
    "warnings_on_use": ["W_TYPE_SEMANTICS_ASSERTED"],
    "minimums": {"rows": 1, "required_feature_completeness": 0.95},
    "reference_ranges": AI4I_REFERENCE_RANGES,
    "applicability": {"margin_fraction": 0.10, "warn_row_fraction": 0.01, "block_row_fraction": 0.30},
    "preprocessing_recipe": "ai4i_features_with_type@1.0.0",
    "model_versions": ["ai4i_failure_clf_typed@Production"]
}

# Reference-dataset evaluation figures, copied from docs/model_cards/*.md (historical 2,000-row test
# partition, Stage 2B baseline). They previously held different, unsourced numbers and invented
# confidence intervals, so /models contradicted the model cards. No CIs exist in the cards -> None.
_TAU = "tau=0.45"
CARD_EVALUATIONS = {
    "NO_TYPE": [
        {"metric_name": "PR-AUC", "metric_value": 0.7734, "subset": None},
        {"metric_name": "ROC-AUC", "metric_value": 0.9763, "subset": None},
        {"metric_name": "Brier", "metric_value": 0.0317, "subset": None},
        {"metric_name": "Precision", "metric_value": 0.4082, "subset": _TAU},
        {"metric_name": "Recall", "metric_value": 0.8824, "subset": _TAU},
        {"metric_name": "F1", "metric_value": 0.5581, "subset": _TAU},
    ],
    "WITH_TYPE": [
        {"metric_name": "PR-AUC", "metric_value": 0.7753, "subset": None},
        {"metric_name": "ROC-AUC", "metric_value": 0.9730, "subset": None},
        {"metric_name": "Brier", "metric_value": 0.0309, "subset": None},
        {"metric_name": "Precision", "metric_value": 0.4041, "subset": _TAU},
        {"metric_name": "Recall", "metric_value": 0.8676, "subset": _TAU},
        {"metric_name": "F1", "metric_value": 0.5514, "subset": _TAU},
    ],
}


def _sync_evaluations(db: Session, model_obj: ModelVersion, evals: list) -> None:
    """Make the stored REFERENCE_DATASET evaluations equal the card values (fixes already-seeded DBs too)."""
    current = db.query(ModelEvaluation).filter(
        ModelEvaluation.model_version_id == model_obj.id,
        ModelEvaluation.evaluation_kind == "REFERENCE_DATASET"
    ).all()
    wanted = {(e["metric_name"], e["subset"], e["metric_value"]) for e in evals}
    have = {(c.metric_name, c.subset, c.metric_value) for c in current}
    if wanted == have:
        return
    for c in current:
        db.delete(c)
    db.flush()
    for ev in evals:
        db.add(ModelEvaluation(
            model_version_id=model_obj.id,
            evaluation_kind="REFERENCE_DATASET",
            split="test",
            metric_name=ev["metric_name"],
            metric_value=ev["metric_value"],
            ci_low=None,
            ci_high=None,
            n_samples=2000,
            subset=ev["subset"],
        ))


def seed_database(db: Session) -> None:
    """Idempotently seed the global tables with platform profiles and categories."""
    # 1. Machine Categories (PRD v1.2 §8.2.2)
    categories = [
        MachineCategory(
            code="GENERAL_MACHINE_TOOL",
            name="General Machine Tool (CNC/Lathe/Mill)",
            eligible_dataset_types=["TABULAR_OPERATING_STATE", "TABULAR_TIMESERIES"],
            eligible_profiles=["ai4i_failure_no_type", "ai4i_failure_with_type"]
        ),
        MachineCategory(
            code="TURBOFAN_ENGINE",
            name="Turbofan Engine",
            eligible_dataset_types=["RUN_TO_FAILURE_MULTIVARIATE"],
            eligible_profiles=["cmapss_rul"]
        ),
        MachineCategory(
            code="BEARING_ROTATING",
            name="Rotating Bearing",
            eligible_dataset_types=["VIBRATION_SIGNAL"],
            eligible_profiles=["paderborn_bearing"]
        ),
        MachineCategory(
            code="ACOUSTIC_MACHINE",
            name="Acoustic Machine (Valve/Pump/Fan/Slide)",
            eligible_dataset_types=["AUDIO_RECORDING"],
            eligible_profiles=["mimii_acoustic"]
        ),
        MachineCategory(
            code="OTHER",
            name="Other Machine",
            eligible_dataset_types=["TABULAR_TIMESERIES"],
            eligible_profiles=["sensor_anomaly"]
        ),
    ]

    for cat in categories:
        existing = db.query(MachineCategory).filter(MachineCategory.code == cat.code).first()
        if not existing:
            db.add(cat)
    db.commit()

    # 2. Pipeline Profiles (PRD v1.2 §8.4.1)
    profiles = [
        (
            "ai4i_failure_no_type", "1.0.0", "A", "NO_TYPE", "REFERENCE_DATASET", AI4I_NO_TYPE_DOC
        ),
        (
            "ai4i_failure_with_type", "1.0.0", "A", "WITH_TYPE", "REFERENCE_DATASET", AI4I_WITH_TYPE_DOC
        ),
    ]

    for pid, ver, pipe, cfg, dom, doc in profiles:
        existing = db.query(PipelineProfile).filter(
            PipelineProfile.profile_id == pid,
            PipelineProfile.version == ver
        ).first()
        if not existing:
            profile = PipelineProfile(
                profile_id=pid,
                version=ver,
                pipeline=pipe,
                configuration=cfg,
                training_domain=dom,
                document=doc,
                is_active=True
            )
            db.add(profile)
    db.commit()

    # 3. Model Versions & Reference Evaluations (PRD v1.2 §10.1, §12.2)
    profile_notype = db.query(PipelineProfile).filter(PipelineProfile.profile_id == "ai4i_failure_no_type").first()
    profile_typed = db.query(PipelineProfile).filter(PipelineProfile.profile_id == "ai4i_failure_with_type").first()

    models = [
        {
            "registry_name": "ai4i_failure_clf_notype",
            "version": "1.0.0",
            "pipeline": "A",
            "configuration": "NO_TYPE",
            "algorithm": "XGBoost",
            "stage": "PRODUCTION",
            "profile_uuid": profile_notype.id,
            "training_domain": "REFERENCE_DATASET",
            "model_scope": "SHARED",
            "default_when_both_runnable": False,  # interim default is NO_TYPE per feasibility
            "thresholds": {"optimal_tau": 0.45, "cost_ratio": 50.0},
            "model_card_uri": "docs/model_cards/ai4i_failure_clf_notype.md",
            "evaluations": CARD_EVALUATIONS["NO_TYPE"],
        },
        {
            "registry_name": "ai4i_failure_clf_typed",
            "version": "1.0.0",
            "pipeline": "A",
            "configuration": "WITH_TYPE",
            "algorithm": "XGBoost",
            "stage": "PRODUCTION",
            "profile_uuid": profile_typed.id,
            "training_domain": "REFERENCE_DATASET",
            "model_scope": "SHARED",
            "default_when_both_runnable": False,
            "thresholds": {"optimal_tau": 0.45, "cost_ratio": 50.0},
            "model_card_uri": "docs/model_cards/ai4i_failure_clf_typed.md",
            "evaluations": CARD_EVALUATIONS["WITH_TYPE"],
        }
    ]

    for m in models:
        m = dict(m)
        evals = m.pop("evaluations")
        model_obj = db.query(ModelVersion).filter(
            ModelVersion.registry_name == m["registry_name"],
            ModelVersion.version == m["version"]
        ).first()
        if not model_obj:
            model_obj = ModelVersion(**m)
            db.add(model_obj)
            db.flush()
        _sync_evaluations(db, model_obj, evals)
    db.commit()
