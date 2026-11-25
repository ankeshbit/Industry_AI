"""
Production Model Loading, Integrity Verification, and Provenance Module
Adheres to:
- PRD v1.2 §10.1, §12.2, §13.5
- Stage 3 Evaluation Architecture v1.4.2 §12.2
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import joblib
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.compatibility import PipelineProfile
from backend.app.models.model import ModelVersion


@dataclass
class LoadedModelBundle:
    model_version_id: str
    model_version: str
    registry_name: str
    configuration: str
    pipeline: Any
    calibrator: Any
    optimal_threshold: float
    feature_names: List[str]
    artifact_path: Path
    artifact_sha256: str
    metadata: Dict[str, Any]
    cost_fn: float = 10000.0
    cost_fp: float = 200.0


# In-memory thread-safe bundle cache keyed by (file_path_str, sha256_hash)
_MODEL_CACHE: Dict[Tuple[str, str], LoadedModelBundle] = {}


def compute_file_checksum(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def clear_model_cache() -> None:
    """Clears in-memory loaded model cache (used in testing and maintenance)."""
    _MODEL_CACHE.clear()


def resolve_expected_artifact(configuration: str) -> Tuple[str, Path, Path]:
    """
    Returns (artifact_filename, artifact_path, metadata_path) for a given configuration.
    Configuration: 'WITH_TYPE' (Config A) or 'NO_TYPE' (Config B).
    """
    cfg_upper = configuration.upper()
    if cfg_upper in ("WITH_TYPE", "A", "CONFIG_A"):
        artifact_file = "production_m2_config_a.joblib"
    elif cfg_upper in ("NO_TYPE", "B", "CONFIG_B"):
        artifact_file = "production_m2_config_b.joblib"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_CONFIGURATION", "message": f"Unsupported model configuration: '{configuration}'."}}
        )

    models_dir = settings.BASE_DIR / "ml" / "artifacts" / "models"
    artifact_path = models_dir / artifact_file
    metadata_path = models_dir / f"{artifact_path.stem}_metadata.json"
    return artifact_file, artifact_path, metadata_path


def validate_model_bundle_structure(bundle: Any, expected_config: str) -> None:
    """
    Validates that a deserialized model bundle adheres strictly to the production contract:
    - Must be a dictionary (Stage 3 production package).
    - Must contain valid scikit-learn pipeline with preprocessor and classifier named steps.
    - Must contain a fitted probability calibrator.
    - Must contain a valid optimal_threshold in (0, 1).
    - Must match expected configuration.
    """
    if not isinstance(bundle, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INVALID_MODEL_BUNDLE", "message": "Loaded artifact is not a valid production model bundle dict."}}
        )

    required_keys = ["pipeline", "calibrator", "optimal_threshold", "feature_names", "configuration"]
    missing = [k for k in required_keys if k not in bundle]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "MALFORMED_MODEL_BUNDLE", "message": f"Model bundle is missing required keys: {missing}"}}
        )

    pipeline = bundle["pipeline"]
    if not hasattr(pipeline, "named_steps"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INVALID_PIPELINE", "message": "Model bundle pipeline missing named_steps attribute."}}
        )

    if "preprocessor" not in pipeline.named_steps or "classifier" not in pipeline.named_steps:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INCOMPLETE_PIPELINE", "message": "Pipeline missing required 'preprocessor' or 'classifier' steps."}}
        )

    calibrator = bundle["calibrator"]
    if calibrator is None or not hasattr(calibrator, "predict_proba"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "MISSING_CALIBRATOR", "message": "Production model requires a fitted probability calibrator."}}
        )

    tau = bundle["optimal_threshold"]
    if not isinstance(tau, (int, float)) or not (0.0 < float(tau) < 1.0):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "INVALID_THRESHOLD", "message": f"Optimal threshold must be a float in (0, 1), got '{tau}'."}}
        )

    bundle_config = str(bundle.get("configuration", "")).upper()
    expected_norm = "WITH_TYPE" if expected_config.upper() in ("WITH_TYPE", "A") else "NO_TYPE"
    if bundle_config != expected_norm:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "CONFIGURATION_MISMATCH", "message": f"Artifact configuration '{bundle_config}' does not match profile '{expected_norm}'."}}
        )


def resolve_and_load_model(db: Session, profile: PipelineProfile) -> LoadedModelBundle:
    """
    Registry-driven production model resolver and loader:
    1. Looks up the active PRODUCTION ModelVersion from the database model registry.
    2. Resolves and validates artifact path.
    3. Verifies artifact existence on disk (503 if missing).
    4. Computes and verifies SHA-256 checksum (500 if corrupted).
    5. Validates pipeline and calibrator structure.
    6. Returns cached LoadedModelBundle.
    """
    # 1. Query database registry
    model_record = db.query(ModelVersion).filter(
        ModelVersion.profile_uuid == profile.id,
        ModelVersion.stage == "PRODUCTION"
    ).order_by(ModelVersion.promoted_at.desc()).first()

    if not model_record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "MODEL_REGISTRY_NOT_FOUND", "message": f"No active PRODUCTION model registered for profile '{profile.profile_id}'."}}
        )

    # 2. Resolve artifact paths
    artifact_file, artifact_path, metadata_path = resolve_expected_artifact(profile.configuration)

    # 3. Verify artifact file exists on disk
    if not artifact_path.exists() or not artifact_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "MODEL_ARTIFACT_NOT_FOUND",
                    "message": (
                        f"Production model artifact '{artifact_file}' was not found on disk at '{artifact_path}'. "
                        "Please run artifact provisioning ('python -m ml.src.models.provision_artifacts') before executing analysis."
                    )
                }
            }
        )

    # 4. Verify checksum
    try:
        actual_sha256 = compute_file_checksum(artifact_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "MODEL_ARTIFACT_UNREADABLE", "message": f"Failed to read model artifact: {str(e)}"}}
        )

    # Read metadata JSON if present to check expected hash
    metadata: Dict[str, Any] = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            expected_hash = metadata.get("artifact_sha256")
            if expected_hash and actual_sha256 != expected_hash:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": {
                            "code": "MODEL_ARTIFACT_CORRUPTED",
                            "message": f"Model artifact '{artifact_file}' failed checksum verification. Expected {expected_hash}, got {actual_sha256}."
                        }
                    }
                )
        except HTTPException:
            raise
        except Exception:
            pass

    # 5. Check in-memory cache
    cache_key = (str(artifact_path), actual_sha256)
    if cache_key in _MODEL_CACHE:
        cached = _MODEL_CACHE[cache_key]
        # Always bind to current database model_record to avoid cross-session ID mismatch
        return LoadedModelBundle(
            model_version_id=model_record.id,
            model_version=model_record.version,
            registry_name=model_record.registry_name,
            configuration=profile.configuration,
            pipeline=cached.pipeline,
            calibrator=cached.calibrator,
            optimal_threshold=cached.optimal_threshold,
            feature_names=cached.feature_names,
            artifact_path=cached.artifact_path,
            artifact_sha256=cached.artifact_sha256,
            metadata=cached.metadata,
            cost_fn=cached.cost_fn,
            cost_fp=cached.cost_fp,
        )

    # 6. Deserialization & validation
    try:
        raw_bundle = joblib.load(artifact_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "MODEL_DESERIALIZATION_FAILED", "message": f"Could not deserialize model artifact '{artifact_file}': {str(e)}"}}
        )

    validate_model_bundle_structure(raw_bundle, profile.configuration)

    optimal_tau = float(raw_bundle["optimal_threshold"])
    feature_names = list(raw_bundle["feature_names"])

    loaded_bundle = LoadedModelBundle(
        model_version_id=model_record.id,
        model_version=model_record.version,
        registry_name=model_record.registry_name,
        configuration=profile.configuration,
        pipeline=raw_bundle["pipeline"],
        calibrator=raw_bundle["calibrator"],
        optimal_threshold=optimal_tau,
        feature_names=feature_names,
        artifact_path=artifact_path,
        artifact_sha256=actual_sha256,
        metadata=metadata or raw_bundle.get("governance", {}),
        cost_fn=float(raw_bundle.get("cost_fn", 10000.0)),
        cost_fp=float(raw_bundle.get("cost_fp", 200.0)),
    )

    _MODEL_CACHE[cache_key] = loaded_bundle
    return loaded_bundle
