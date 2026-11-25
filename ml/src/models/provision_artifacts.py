"""
Model Artifact Provisioning Script (PRD v1.2 §10.1, §11.1)
Verifies and provisions production model artifacts:
- production_m2_config_a.joblib (WITH_TYPE)
- production_m2_config_b.joblib (NO_TYPE)

Idempotent:
- If artifacts exist, match metadata checksums, and pass structural validation, no retraining is performed.
- If missing or corrupted, regenerates them via deterministic Stage 3 pipeline.
"""

import sys
import json
import hashlib
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import joblib

MODELS_DIR = ROOT_DIR / "ml" / "artifacts" / "models"


def compute_file_checksum(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_artifact(config_code: str) -> bool:
    """Checks whether an artifact exists, matches its metadata checksum, and is structurally valid."""
    suffix = "a" if config_code.lower() == "a" else "b"
    joblib_path = MODELS_DIR / f"production_m2_config_{suffix}.joblib"
    meta_path = MODELS_DIR / f"production_m2_config_{suffix}_metadata.json"

    if not joblib_path.exists() or not meta_path.exists():
        return False

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        expected_hash = meta.get("artifact_sha256")
        actual_hash = compute_file_checksum(joblib_path)
        if expected_hash and actual_hash != expected_hash:
            print(f"[Provisioning] Checksum mismatch for Config {config_code.upper()}: expected {expected_hash}, got {actual_hash}")
            return False

        # Load and validate bundle structure
        bundle = joblib.load(joblib_path)
        if not isinstance(bundle, dict):
            return False
        for req in ["pipeline", "calibrator", "optimal_threshold", "feature_names", "configuration"]:
            if req not in bundle:
                return False
        if not hasattr(bundle["pipeline"], "named_steps"):
            return False
        if "preprocessor" not in bundle["pipeline"].named_steps or "classifier" not in bundle["pipeline"].named_steps:
            return False
        if bundle["calibrator"] is None or not hasattr(bundle["calibrator"], "predict_proba"):
            return False
        if not (0.0 < float(bundle["optimal_threshold"]) < 1.0):
            return False
        return True
    except Exception as e:
        print(f"[Provisioning] Validation error for Config {config_code.upper()}: {e}")
        return False


def provision_artifacts(force_retrain: bool = False) -> int:
    """Provisions all required production model artifacts."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    configs = ["a", "b"]
    all_valid = True

    print(f"[Provisioning] Checking production model artifacts in {MODELS_DIR}...")
    for cfg in configs:
        valid = False if force_retrain else verify_artifact(cfg)
        if valid:
            print(f"[Provisioning] [OK] Config {cfg.upper()} artifact is valid and verified.")
        else:
            all_valid = False
            print(f"[Provisioning] [MISSING/INVALID] Config {cfg.upper()} artifact needs generation.")

    if all_valid:
        print("[Provisioning] All production model artifacts are present, verified, and ready.")
        return 0

    print("[Provisioning] Generating missing production artifacts using authoritative training pipeline...")
    from ml.src.models.train_production_model import train_and_package_production_model

    for cfg in configs:
        if force_retrain or not verify_artifact(cfg):
            print(f"\n--- Training Production Model Config {cfg.upper()} ---")
            train_and_package_production_model(cfg.upper())
            if not verify_artifact(cfg):
                print(f"[Provisioning] [FAIL] Newly generated artifact for Config {cfg.upper()} failed verification!")
                return 1
            print(f"[Provisioning] [SUCCESS] Config {cfg.upper()} successfully trained, packaged, and verified.")

    print("\n[Provisioning] All production model artifacts provisioned successfully.")
    return 0


if __name__ == "__main__":
    force = "--force" in sys.argv
    sys.exit(provision_artifacts(force_retrain=force))
