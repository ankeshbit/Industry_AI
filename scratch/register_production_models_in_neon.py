"""
Registers promoted Stage 3 M2 production models in Neon PostgreSQL model registry.
Archives 1.0.0 versions and sets 3.0.0 versions to PRODUCTION.
"""

import sys
from pathlib import Path
from datetime import datetime

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.database import SessionLocal
from backend.app.models.compatibility import PipelineProfile
from backend.app.models.model import ModelVersion, ModelEvaluation


def register_models():
    db = SessionLocal()
    try:
        # 1. Fetch profiles
        p_typed = db.query(PipelineProfile).filter(PipelineProfile.configuration == "WITH_TYPE").first()
        p_notype = db.query(PipelineProfile).filter(PipelineProfile.configuration == "NO_TYPE").first()
        assert p_typed and p_notype, "Missing pipeline profiles in database"

        # 2. Archive older 1.0.0 versions
        db.query(ModelVersion).filter(ModelVersion.version == "1.0.0").update({"stage": "ARCHIVED"})
        db.commit()

        # 3. Check or insert 3.0.0 for WITH_TYPE
        mv_typed = db.query(ModelVersion).filter(
            ModelVersion.registry_name == "ai4i_failure_clf_typed",
            ModelVersion.version == "3.0.0"
        ).first()
        if not mv_typed:
            mv_typed = ModelVersion(
                registry_name="ai4i_failure_clf_typed",
                version="3.0.0",
                pipeline="A",
                configuration="WITH_TYPE",
                task="BINARY_CLASSIFICATION",
                algorithm="XGBoost (M2 + Platt Calibrated)",
                stage="PRODUCTION",
                profile_uuid=p_typed.id,
                training_domain="REFERENCE_DATASET",
                model_scope="SHARED",
                default_when_both_runnable=True,
                reference_ranges_uri="ml/artifacts/reference_ranges.json",
                thresholds={
                    "optimal_tau": 0.0100,
                    "cost_ratio": 50.0,
                    "bayes_tau": 0.01961,
                    "method": "stage3_cost_sensitive_out_of_sample"
                },
                dataset_hash="dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e",
                model_card_uri="docs/model_cards/ai4i_failure_clf_typed.md",
                promoted_at=datetime.utcnow(),
            )
            db.add(mv_typed)
            db.flush()
        else:
            mv_typed.stage = "PRODUCTION"
            mv_typed.algorithm = "XGBoost (M2 + Platt Calibrated)"
            mv_typed.model_card_uri = "docs/model_cards/ai4i_failure_clf_typed.md"
            mv_typed.thresholds = {
                "optimal_tau": 0.0100,
                "cost_ratio": 50.0,
                "bayes_tau": 0.01961,
                "method": "stage3_cost_sensitive_out_of_sample"
            }
            db.query(ModelEvaluation).filter(ModelEvaluation.model_version_id == mv_typed.id).delete()

        # Add evaluation records for WITH_TYPE
        metrics_typed = [
            ("PR-AUC", 0.76165),
            ("ROC-AUC", 0.96881),
            ("BrierScore", 0.014822),
            ("BrierSkillScore", 0.54870),
            ("OperationalCost", 77200.0),
            ("Precision", 0.2159),
            ("Recall", 0.9559),
            ("F1-Score", 0.3523),
        ]
        for m_name, m_val in metrics_typed:
            db.add(ModelEvaluation(
                model_version_id=mv_typed.id,
                evaluation_kind="REFERENCE_DATASET",
                split="test",
                metric_name=m_name,
                metric_value=m_val,
                n_samples=2000,
            ))

        # 4. Check or insert 3.0.0 for NO_TYPE
        mv_notype = db.query(ModelVersion).filter(
            ModelVersion.registry_name == "ai4i_failure_clf_notype",
            ModelVersion.version == "3.0.0"
        ).first()
        if not mv_notype:
            mv_notype = ModelVersion(
                registry_name="ai4i_failure_clf_notype",
                version="3.0.0",
                pipeline="A",
                configuration="NO_TYPE",
                task="BINARY_CLASSIFICATION",
                algorithm="XGBoost (M2 + Platt Calibrated)",
                stage="PRODUCTION",
                profile_uuid=p_notype.id,
                training_domain="REFERENCE_DATASET",
                model_scope="SHARED",
                default_when_both_runnable=False,
                reference_ranges_uri="ml/artifacts/reference_ranges.json",
                thresholds={
                    "optimal_tau": 0.0100,
                    "cost_ratio": 50.0,
                    "bayes_tau": 0.01961,
                    "method": "stage3_cost_sensitive_out_of_sample"
                },
                dataset_hash="dc6630cd9b1f0f853922fad78a1b6436570d3f1ec863f1dd5c4340ac56bc8a8e",
                model_card_uri="docs/model_cards/ai4i_failure_clf_notype.md",
                promoted_at=datetime.utcnow(),
            )
            db.add(mv_notype)
            db.flush()
        else:
            mv_notype.stage = "PRODUCTION"
            mv_notype.algorithm = "XGBoost (M2 + Platt Calibrated)"
            mv_notype.model_card_uri = "docs/model_cards/ai4i_failure_clf_notype.md"
            mv_notype.thresholds = {
                "optimal_tau": 0.0100,
                "cost_ratio": 50.0,
                "bayes_tau": 0.01961,
                "method": "stage3_cost_sensitive_out_of_sample"
            }
            db.query(ModelEvaluation).filter(ModelEvaluation.model_version_id == mv_notype.id).delete()

        # Add evaluation records for NO_TYPE
        metrics_notype = [
            ("PR-AUC", 0.73822),
            ("ROC-AUC", 0.97159),
            ("BrierScore", 0.014970),
            ("BrierSkillScore", 0.54421),
            ("OperationalCost", 72400.0),
            ("Precision", 0.2347),
            ("Recall", 0.9559),
            ("F1-Score", 0.3768),
        ]
        for m_name, m_val in metrics_notype:
            db.add(ModelEvaluation(
                model_version_id=mv_notype.id,
                evaluation_kind="REFERENCE_DATASET",
                split="test",
                metric_name=m_name,
                metric_value=m_val,
                n_samples=2000,
            ))

        db.commit()
        print("Successfully registered production model versions in Neon PostgreSQL!")
        print(f"WITH_TYPE: id={mv_typed.id}, version=3.0.0, stage=PRODUCTION")
        print(f"NO_TYPE: id={mv_notype.id}, version=3.0.0, stage=PRODUCTION")

    except Exception as e:
        db.rollback()
        print(f"Error registering models: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    register_models()
