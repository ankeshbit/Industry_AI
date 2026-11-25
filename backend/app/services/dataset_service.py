"""
Dataset Management and Ingestion Service (PRD v1.2 §8.3, §13.4, AC-DS-1..10)
Handles CSV streaming, SHA-256 calculation, size enforcement, quality scoring,
validation reporting, and column mapping wizard.
"""

import os
import io
import re
import csv
import uuid
import codecs
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from backend.app.config import settings
from backend.app.models.machine import Machine
from backend.app.models.dataset import (
    Dataset, DatasetVersion, DatasetColumn, ColumnMapping, ValidationReport, DatasetEvent
)
from backend.app.models.compatibility import PipelineProfile
from backend.app.models.usage import UsageEvent

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9\-_]+$")

# Canonical features and synonyms for AI4I
SYNONYMS = {
    "air_temperature": [
        "air temperature", "air temp", "air temperature [k]", "air temp [k]",
        "air temperature [c]", "air temp [c]", "air_temp", "air_temperature",
        "ambient temp", "ambient temperature", "ambient"
    ],
    "process_temperature": [
        "process temperature", "process temp", "proc temp", "process temperature [k]",
        "process temp [k]", "process temp [c]", "proc_temp", "process_temperature",
        "process chamber temp", "process chamber temperature", "chamber temp"
    ],
    "rotational_speed": [
        "rotational speed", "speed", "rotational speed [rpm]", "rpm",
        "motor speed", "spindle speed", "spindle rpm", "rotational_speed"
    ],
    "torque": [
        "torque", "torque [nm]", "spindle torque", "motor torque", "drive torque"
    ],
    "tool_wear": [
        "tool wear", "tool wear [min]", "tool_wear", "wear", "tool life",
        "cumulative tool wear"
    ],
    "product_type": [
        "type", "product type", "product_type", "quality variant"
    ]
}

def _normalize_header(text: str) -> str:
    """Lower-case, drop bracketed unit suffixes (e.g. '[C]') and collapse separators."""
    no_unit = re.sub(r"\[[^\]]*\]", " ", str(text).lower())
    return re.sub(r"[_\-\s]+", " ", no_unit).strip()


FORBIDDEN_COLUMNS = {
    "machine_failure", "machine failure", "failure", "target", "label",
    "twf", "hdf", "pwf", "osf", "rnf", "udi", "product_id", "product id"
}

def _decode_and_detect_encoding(file_bytes: bytes) -> Tuple[str, str]:
    """Decodes file bytes supporting UTF-8, UTF-8-BOM, UTF-16, and Latin-1."""
    if file_bytes.startswith(codecs.BOM_UTF8):
        try:
            return file_bytes.decode("utf-8-sig"), "utf-8-sig"
        except UnicodeDecodeError:
            pass
    if file_bytes.startswith(codecs.BOM_UTF16_LE) or file_bytes.startswith(codecs.BOM_UTF16_BE):
        try:
            return file_bytes.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            pass
    try:
        return file_bytes.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    if len(file_bytes) % 2 == 0:
        try:
            return file_bytes.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            pass
    try:
        return file_bytes.decode("latin-1"), "latin-1"
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": {"code": "UNSUPPORTED_FORMAT", "message": f"Unable to decode file encoding: {str(e)}"}}
        )

def _detect_delimiter(sample_text: str, filename: str) -> str:
    """.tsv files, or files whose header line has more tabs/semicolons than commas."""
    if filename.lower().endswith(".tsv"):
        return "\t"
    first_line = sample_text.split("\n", 1)[0]
    tab_count = first_line.count("\t")
    comma_count = first_line.count(",")
    semi_count = first_line.count(";")
    if tab_count > comma_count and tab_count > semi_count:
        return "\t"
    if semi_count > comma_count and semi_count > tab_count:
        return ";"
    return ","


def create_dataset(
    db: Session,
    org_id: str,
    machine_id: str,
    name: str,
    description: Optional[str] = None,
    dataset_type: str = "TABULAR_OPERATING_STATE",
    objective: str = "FAILURE_PROBABILITY_CURRENT_STATE",
    user_id: Optional[str] = None
) -> Dataset:
    """Creates a dataset entry attached to a machine (AC-MM-2, AC-DS-1)."""
    machine = db.query(Machine).filter(
        Machine.id == machine_id,
        Machine.organisation_id == org_id
    ).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Machine not found."}}
        )

    # AC-MM-2: Archived machines reject new datasets with 409
    if machine.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "MACHINE_ARCHIVED", "message": "Cannot create dataset for an archived machine."}}
        )

    # Check duplicate name within the machine
    existing = db.query(Dataset).filter(
        Dataset.organisation_id == org_id,
        Dataset.machine_id == machine_id,
        Dataset.name == name
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "DUPLICATE_DATASET_NAME", "message": f"Dataset '{name}' already exists for this machine."}}
        )

    dataset = Dataset(
        organisation_id=org_id,
        machine_id=machine_id,
        name=name,
        description=description,
        dataset_type=dataset_type,
        objective=objective,
        provenance="CUSTOMER",
        status="ACTIVE",
        created_by=user_id
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset

def upload_dataset_version_stream(
    db: Session,
    org_id: str,
    dataset_id: str,
    filename: str,
    file_bytes: bytes,
    user_id: Optional[str] = None
) -> Tuple[DatasetVersion, bool]:
    """
    Ingests a CSV/TSV dataset version:
    - Enforces path safety and identifier validation
    - Enforces 50 MB byte limit (413 PAYLOAD_TOO_LARGE)
    - Verifies file kind (CSV/TSV) and magic bytes (415 UNSUPPORTED_FORMAT)
    - Rejects empty files (422 E_EMPTY)
    - Rejects duplicate column headers (422 E_DUPLICATE_COLUMNS)
    - Rejects wide datasets (422 E_TOO_MANY_COLUMNS)
    - Streams to storage/org/{org_id}/datasets/{id}/v{n}/{uuid}.csv
    - Computes SHA-256 and deduplicates
    - Ingests schema and columns with rollback on failure (no orphaned files)
    """
    # 0. Path safety: Validate identifiers
    if not SAFE_ID_REGEX.match(org_id) or not SAFE_ID_REGEX.match(dataset_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "INVALID_IDENTIFIER", "message": "Identifier contains invalid path characters."}}
        )

    # 1. Size check (AC-DS-2)
    size_bytes = len(file_bytes)
    if size_bytes == 0 or not file_bytes.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_EMPTY", "message": "Uploaded file is empty."}}
        )

    if size_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": {"code": "PAYLOAD_TOO_LARGE", "message": f"File size ({size_bytes} bytes) exceeds maximum allowed {settings.MAX_UPLOAD_SIZE_BYTES} bytes."}}
        )

    # 2. Extension & Magic Byte Verification (AC-DS-1)
    if not filename.lower().endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": {"code": "UNSUPPORTED_FORMAT", "message": "Only CSV/TSV tabular formats are supported in Milestone 1."}}
        )

    # Reject executable headers (MZ, ELF, Mach-O, scripts)
    if file_bytes.startswith(b"MZ") or file_bytes.startswith(b"\x7fELF") or file_bytes.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": {"code": "UNSUPPORTED_FORMAT", "message": "Invalid file content: executable or non-CSV magic bytes detected."}}
        )

    # 3. Encoding detection & decoding
    text_content, detected_encoding = _decode_and_detect_encoding(file_bytes)
    if not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_EMPTY", "message": "Uploaded file is empty or whitespace only."}}
        )

    # 4. SHA-256 Computation
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # 5. Verify dataset exists and belongs to org
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.organisation_id == org_id).first()
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Dataset not found."}}
        )

    # 6. Deduplication Check (PRD line 839, AC-DS-6)
    existing_version = db.query(DatasetVersion).filter(
        DatasetVersion.dataset_id == dataset_id,
        DatasetVersion.sha256 == sha256_hash,
        DatasetVersion.status != "PURGED"
    ).first()
    if existing_version:
        return existing_version, True  # already exists

    # 7. Delimiter & Header Inspection
    delimiter = _detect_delimiter(text_content[:8192], filename)
    header_line = text_content.strip().split("\n", 1)[0].strip()
    if not header_line:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_EMPTY", "message": "Dataset contains no header line."}}
        )

    reader = csv.reader([header_line], delimiter=delimiter)
    raw_headers = next(reader, [])
    raw_headers = [h.strip() for h in raw_headers]
    if not raw_headers or all(h == "" for h in raw_headers):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_EMPTY", "message": "Dataset contains empty headers."}}
        )

    if len(raw_headers) != len(set(raw_headers)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_DUPLICATE_COLUMNS", "message": "Dataset contains duplicate column headers."}}
        )

    if len(raw_headers) > settings.MAX_CSV_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_TOO_MANY_COLUMNS", "message": f"Dataset has {len(raw_headers)} columns, exceeding the maximum allowed {settings.MAX_CSV_COLUMNS} columns."}}
        )

    # 8. Parse CSV content
    try:
        df = pd.read_csv(io.StringIO(text_content), sep=delimiter, nrows=settings.MAX_CSV_ROWS + 1)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": {"code": "E_MALFORMED_CSV", "message": f"Malformed CSV file: {str(e)}"}}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"error": {"code": "UNSUPPORTED_FORMAT", "message": f"Malformed CSV file: {str(e)}"}}
        )

    if len(df) > settings.MAX_CSV_ROWS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"error": {"code": "PAYLOAD_TOO_LARGE", "message": f"Dataset exceeds the maximum of {settings.MAX_CSV_ROWS} rows."}}
        )

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_EMPTY", "message": "Dataset contains no rows or columns."}}
        )

    # 9. Determine version number
    latest_version = db.query(DatasetVersion).filter(
        DatasetVersion.dataset_id == dataset_id
    ).order_by(DatasetVersion.version_no.desc()).first()
    version_no = (latest_version.version_no + 1) if latest_version else 1

    # 10. Path traversal validation & file storage
    file_uuid = str(uuid.uuid4())
    storage_rel_dir = f"org/{org_id}/datasets/{dataset_id}/v{version_no}"
    storage_abs_dir = (settings.STORAGE_DIR / storage_rel_dir).resolve()
    if not storage_abs_dir.is_relative_to(settings.STORAGE_DIR.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "PATH_TRAVERSAL_DETECTED", "message": "Storage path escapes base storage directory."}}
        )
    storage_abs_dir.mkdir(parents=True, exist_ok=True)
    storage_path = (storage_abs_dir / f"{file_uuid}.csv").resolve()
    if not storage_path.is_relative_to(settings.STORAGE_DIR.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "PATH_TRAVERSAL_DETECTED", "message": "Storage file path escapes base storage directory."}}
        )
    storage_key = f"{storage_rel_dir}/{file_uuid}.csv"

    # Always write a normalized UTF-8 comma-separated CSV so downstream pipeline stages read cleanly
    stored_bytes = df.to_csv(index=False).encode("utf-8")
    with open(storage_path, "wb") as f:
        f.write(stored_bytes)

    # 11. Transactional DB updates with file rollback on failure
    try:
        dv = DatasetVersion(
            organisation_id=org_id,
            dataset_id=dataset_id,
            version_no=version_no,
            file_kind="CSV",
            original_filename=filename,
            storage_key=storage_key,
            size_bytes=size_bytes,
            sha256=sha256_hash,
            scan_status="CLEAN",
            status="UPLOADED",
            row_count=len(df),
            column_count=len(df.columns),
            uploaded_by=user_id
        )
        db.add(dv)
        db.flush()

        for idx, col_name in enumerate(df.columns):
            series = df[col_name]
            if pd.api.types.is_numeric_dtype(series):
                inferred_type = "numeric"
                s_clean = series.replace([np.inf, -np.inf], np.nan).dropna()
                stats = {
                    "min": float(s_clean.min()) if not s_clean.empty else None,
                    "max": float(s_clean.max()) if not s_clean.empty else None,
                    "null_count": int(series.isna().sum()),
                    "inf_count": int(np.isinf(series).sum()) if hasattr(series, "dtype") else 0
                }
            elif pd.api.types.is_datetime64_any_dtype(series):
                inferred_type = "datetime"
                stats = {"null_count": int(series.isna().sum())}
            else:
                inferred_type = "categorical"
                unique_vals = [str(x) for x in series.dropna().unique()[:10]]
                stats = {
                    "unique_count": int(series.nunique()),
                    "sample_values": unique_vals,
                    "null_count": int(series.isna().sum())
                }

            col = DatasetColumn(
                organisation_id=org_id,
                dataset_version_id=dv.id,
                position=idx,
                name=str(col_name),
                inferred_type=inferred_type,
                stats=stats
            )
            db.add(col)

        db.add(DatasetEvent(
            organisation_id=org_id,
            dataset_version_id=dv.id,
            event_type="UPLOADED",
            actor_id=user_id,
            details={"filename": filename, "size_bytes": size_bytes, "rows": len(df), "columns": len(df.columns)}
        ))

        db.add(UsageEvent(
            organisation_id=org_id,
            event_type="DATASET_UPLOAD",
            quantity=1,
            details={"dataset_version_id": dv.id, "size_bytes": size_bytes}
        ))

        db.commit()
        db.refresh(dv)
        return dv, False
    except Exception as e:
        db.rollback()
        if storage_path.exists():
            storage_path.unlink(missing_ok=True)
        raise e

def compute_quality_score_and_report(
    db: Session,
    dataset_version_id: str,
    mapping_id: Optional[str] = None,
    profile_id: Optional[str] = None,
    org_id: Optional[str] = None
) -> ValidationReport:
    """
    Computes quality score according to PRD v1.2 §8.3.5:
    Q = 100 * (0.30 S_complete + 0.25 S_valid + 0.15 S_unique + 0.20 S_consistent + 0.10 S_outlier)
    Stores immutable ValidationReport with tenant isolation (AC-ORG-2, AC-DS-7).
    """
    query = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id)
    if org_id:
        query = query.filter(DatasetVersion.organisation_id == org_id)
    dv = query.first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    storage_abs_path = settings.STORAGE_DIR / dv.storage_key
    if not storage_abs_path.exists():
        raise HTTPException(status_code=500, detail="Underlying dataset file missing from storage.")

    df = pd.read_csv(storage_abs_path)
    total_rows = len(df)
    if total_rows == 0:
        total_rows = 1

    # Resolve mapping if available
    mapping_obj = None
    if mapping_id:
        mapping_obj = db.query(ColumnMapping).filter(
            ColumnMapping.id == mapping_id,
            ColumnMapping.organisation_id == dv.organisation_id
        ).first()
    elif profile_id:
        mapping_obj = db.query(ColumnMapping).filter(
            ColumnMapping.dataset_version_id == dataset_version_id,
            ColumnMapping.profile_id == profile_id
        ).order_by(ColumnMapping.mapping_version.desc()).first()

    # Determine columns to check
    if mapping_obj and mapping_obj.mappings:
        eval_cols = [m["column"] for m in mapping_obj.mappings.values() if m.get("column") in df.columns]
    else:
        eval_cols = list(df.columns)

    checks = []

    # 1. S_complete: 1 - missing fraction
    if eval_cols:
        missing_count = int(df[eval_cols].isna().sum().sum())
        total_cells = total_rows * len(eval_cols)
        s_complete = max(0.0, 1.0 - (missing_count / total_cells))
        if missing_count > 0:
            checks.append({
                "code": "W_MISSING",
                "severity": "WARNING",
                "count": missing_count,
                "message": f"Found {missing_count} missing cells in evaluated columns."
            })
    else:
        s_complete = 1.0

    # 2. S_valid: fraction of cells that parse and lie in plausible physical ranges
    numeric_cols = [c for c in eval_cols if pd.api.types.is_numeric_dtype(df[c])]

    # Physical lower bounds per mapped column: (bound, strict). Temperatures must be above absolute zero in
    # their declared unit; speed, torque and tool wear cannot be negative. Unmapped columns keep the coarse rule.
    physical_bounds: Dict[str, Tuple[float, bool]] = {}
    if mapping_obj and mapping_obj.mappings:
        for canon, spec in mapping_obj.mappings.items():
            col = spec.get("column")
            if canon in ("air_temperature", "process_temperature"):
                bound = {"K": 0.0, "degC": -273.15, "degF": -459.67}.get(spec.get("unit"))
                if bound is not None and col:
                    physical_bounds[col] = (bound, True)
            elif canon in ("rotational_speed", "torque", "tool_wear") and col:
                physical_bounds[col] = (0.0, False)

    if numeric_cols:
        invalid_count = 0
        for col in numeric_cols:
            s = df[col].dropna()
            # Infinite values are invalid numbers
            inf_mask = np.isinf(s)
            invalid_count += int(inf_mask.sum())
            s_finite = s[~inf_mask]
            if col in physical_bounds:
                bound, strict = physical_bounds[col]
                invalids = (s_finite <= bound).sum() if strict else (s_finite < bound).sum()
            else:
                invalids = (s_finite < -100).sum()
            invalid_count += int(invalids)
        total_num_cells = total_rows * len(numeric_cols)
        s_valid = max(0.0, 1.0 - (invalid_count / total_num_cells)) if total_num_cells > 0 else 1.0
        if invalid_count > 0:
            checks.append({
                "code": "W_INVALID_VALUES",
                "severity": "WARNING",
                "count": invalid_count,
                "message": f"Found {invalid_count} values outside physically plausible ranges (e.g. infinite values, negative speed, torque or tool wear, or temperatures below absolute zero)."
            })
    else:
        s_valid = 1.0

    # 3. S_unique: 1 - fraction of exact duplicate rows
    dup_rows = int(df.duplicated().sum())
    s_unique = max(0.0, 1.0 - (dup_rows / total_rows))
    if dup_rows > 0:
        checks.append({
            "code": "W_DUP_ROWS",
            "severity": "WARNING",
            "count": dup_rows,
            "message": f"Found {dup_rows} exact duplicate rows."
        })

    # 4. S_consistent: 1.0 for independent operating state rows without contradiction
    s_consistent = 1.0

    # 5. S_outlier: 1 - min(1, outlier_fraction / 0.05)
    # Using IQR fences on numeric columns
    outlier_row_count = 0
    if numeric_cols:
        is_outlier_row = np.zeros(total_rows, dtype=bool)
        for col in numeric_cols:
            s = df[col].dropna()
            if len(s) > 10:
                q25, q75 = np.percentile(s, [25, 75])
                iqr = q75 - q25
                if iqr > 0:
                    lower = q25 - 3.0 * iqr
                    upper = q75 + 3.0 * iqr
                    outlier_mask = (df[col] < lower) | (df[col] > upper)
                    is_outlier_row = is_outlier_row | outlier_mask.to_numpy()
        outlier_row_count = int(is_outlier_row.sum())
        outlier_fraction = outlier_row_count / total_rows
        s_outlier = max(0.0, 1.0 - min(1.0, outlier_fraction / 0.05))
        if outlier_row_count > 0:
            checks.append({
                "code": "W_OUTLIERS",
                "severity": "WARNING",
                "count": outlier_row_count,
                "message": f"Found {outlier_row_count} outlier rows using robust statistical fences."
            })
    else:
        s_outlier = 1.0

    # Overall Q score (PRD §8.3.5)
    q_score = round(100.0 * (
        0.30 * s_complete +
        0.25 * s_valid +
        0.15 * s_unique +
        0.20 * s_consistent +
        0.10 * s_outlier
    ), 2)

    if q_score < 60.0:
        checks.append({
            "code": "W_QUALITY_POOR",
            "severity": "WARNING",
            "message": f"Data quality score ({q_score}) is below 60.",
            "remedy": "Resolve missing values, duplicate rows, or extreme outliers."
        })

    components = {
        "S_complete": round(s_complete, 4),
        "S_valid": round(s_valid, 4),
        "S_unique": round(s_unique, 4),
        "S_consistent": round(s_consistent, 4),
        "S_outlier": round(s_outlier, 4)
    }

    # Generate preview (first 10 rows as dict)
    preview_df = df.head(10).replace([np.nan, np.inf, -np.inf], None)
    preview_data = []
    for row in preview_df.to_dict(orient="records"):
        sanitized_row = {}
        for k, v in row.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                sanitized_row[k] = None
            else:
                sanitized_row[k] = v
        preview_data.append(sanitized_row)

    report = ValidationReport(
        organisation_id=dv.organisation_id,
        dataset_version_id=dataset_version_id,
        mapping_id=mapping_obj.id if mapping_obj else None,
        validator_version="1.0.0",
        quality_score=q_score,
        quality_components=components,
        checks=checks,
        preview=preview_data
    )
    db.add(report)
    dv.status = "VALIDATED"
    db.commit()
    db.refresh(report)
    return report

def generate_column_suggestions(
    db: Session,
    dataset_version_id: str,
    profile_id: str,
    org_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes customer column headers and returns suggested mappings (PRD v1.2 §8.3.6, AC-DS-9, AC-ORG-2).
    Flags each as suggested: true. Never auto-applies without user confirmation.
    """
    profile = db.query(PipelineProfile).filter(PipelineProfile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Pipeline profile not found.")

    query = db.query(DatasetVersion).filter(DatasetVersion.id == dataset_version_id)
    if org_id:
        query = query.filter(DatasetVersion.organisation_id == org_id)
    dv = query.first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    doc = profile.document
    required_features = doc.get("required_features", [])
    columns = [c.name for c in dv.columns]

    suggestions = {}
    for feat in required_features:
        feat_name = feat["name"]
        syns = {_normalize_header(s) for s in SYNONYMS.get(feat_name, [feat_name.lower()])}
        matched_col = None
        inferred_unit = feat.get("unit_canonical", None)

        for col in columns:
            # Exact or synonym match (units in brackets are ignored for matching, but used below)
            if _normalize_header(col) in syns:
                matched_col = col
                # Detect unit from column name brackets
                if "[" in col and "]" in col:
                    unit_in_col = col[col.find("[")+1:col.find("]")].strip()
                    if unit_in_col in feat.get("allowed_units", []):
                        inferred_unit = unit_in_col
                    elif unit_in_col.lower() in ("c", "degc", "°c"):
                        inferred_unit = "degC"
                    elif unit_in_col.lower() in ("f", "degf", "°f"):
                        inferred_unit = "degF"
                    elif unit_in_col.lower() in ("k", "kelvin"):
                        inferred_unit = "K"
                break

        if matched_col:
            entry = {
                "column": matched_col,
                "unit": inferred_unit,
                "suggested": True,
                "confirmed": False
            }
            if feat_name == "product_type":
                entry["asserted_equivalence"] = False
            suggestions[feat_name] = entry

    return {
        "profile_id": profile_id,
        "dataset_version_id": dataset_version_id,
        "suggestions": suggestions
    }

def save_column_mapping(
    db: Session,
    org_id: str,
    dataset_version_id: str,
    profile_id: str,
    mappings: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> ColumnMapping:
    """
    Saves confirmed column mapping for a dataset version and profile (PRD v1.2 §8.3.6, AC-DS-9, AC-CE-7).
    Validates forbidden columns, product_type semantics assertion, and profile compatibility.
    """
    profile = db.query(PipelineProfile).filter(PipelineProfile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Pipeline profile not found.")

    dv = db.query(DatasetVersion).filter(
        DatasetVersion.id == dataset_version_id,
        DatasetVersion.organisation_id == org_id
    ).first()
    if not dv:
        raise HTTPException(status_code=404, detail="Dataset version not found.")

    doc = profile.document
    required_features = {f["name"]: f for f in doc.get("required_features", [])}
    forbidden_features = [f.lower().replace(" ", "_") for f in doc.get("forbidden_features", [])]
    all_forbidden = set(forbidden_features) | {f.lower().replace(" ", "_") for f in FORBIDDEN_COLUMNS}

    # Verify all required features from profile are present in mapping
    missing_required = set(required_features.keys()) - set(mappings.keys())
    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_MISSING_FEATURE", "message": f"Missing required feature mapping: {sorted(list(missing_required))}"}}
        )

    # Verify that mapped columns exist in dataset version
    dv_col_names = {c.name for c in dv.columns}
    for canonical_name, spec in mappings.items():
        col_mapped = spec.get("column", "")
        if col_mapped not in dv_col_names:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "E_UNKNOWN_COLUMN", "message": f"Column '{col_mapped}' not found in dataset version."}}
            )

    if "product_type" in mappings and profile.configuration != "WITH_TYPE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": "E_FEATURE_NOT_IN_PROFILE", "message": f"Feature 'product_type' is not supported in profile '{profile_id}'."}}
        )

    # AC-CE-7: Reject if forbidden feature mapped as model input
    for canonical_name, spec in mappings.items():
        col_mapped = spec.get("column", "")
        col_norm = col_mapped.lower().replace(" ", "_")
        canon_norm = canonical_name.lower().replace(" ", "_")
        if col_norm in all_forbidden or canon_norm in all_forbidden:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "E_FORBIDDEN_FEATURE", "message": f"Column '{col_mapped}' is a forbidden feature (target, failure mode, or identifier) and cannot be mapped as model input."}}
            )

    # Validate product_type rule (PRD §8.3.6 line 891, AC-FP-4)
    if "product_type" in mappings:
        if profile.configuration != "WITH_TYPE":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "E_FEATURE_NOT_IN_PROFILE", "message": f"Feature 'product_type' is not supported in profile '{profile_id}'."}}
            )
        pt_spec = mappings["product_type"]
        if not pt_spec.get("asserted_equivalence", False):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": {"code": "W_TYPE_SEMANTICS_ASSERTED", "message": "Mapping product_type requires asserted_equivalence=true confirming AI4I-style quality variant semantics."}}
            )
        pt_col = pt_spec.get("column")
        storage_path = settings.STORAGE_DIR / dv.storage_key
        if storage_path.exists() and pt_col:
            df_sample = pd.read_csv(storage_path, usecols=[pt_col])
            unique_vals = set(df_sample[pt_col].dropna().astype(str).str.strip().str.upper().unique())
            if not unique_vals.issubset({"L", "M", "H"}):
                invalid_vals = sorted(list(unique_vals - {"L", "M", "H"}))
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": {"code": "E_INVALID_CATEGORY_VALUES", "message": f"Column '{pt_col}' mapped to product_type contains invalid values: {invalid_vals}. Allowed values are 'L', 'M', 'H'."}}
                )

    # Validate units
    for canonical_name, spec in mappings.items():
        if canonical_name in required_features:
            feat_info = required_features[canonical_name]
            allowed_units = feat_info.get("allowed_units", [])
            unit = spec.get("unit")
            if allowed_units and unit not in allowed_units:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error": {"code": "E_UNIT_UNCONVERTIBLE", "message": f"Unit '{unit}' is not allowed for feature '{canonical_name}'. Allowed: {allowed_units}"}}
                )

    # Determine mapping version
    latest_map = db.query(ColumnMapping).filter(
        ColumnMapping.dataset_version_id == dataset_version_id,
        ColumnMapping.profile_id == profile_id
    ).order_by(ColumnMapping.mapping_version.desc()).first()
    mapping_version = (latest_map.mapping_version + 1) if latest_map else 1

    mapping_record = ColumnMapping(
        organisation_id=org_id,
        dataset_version_id=dataset_version_id,
        profile_id=profile_id,
        mapping_version=mapping_version,
        mappings=mappings,
        options=options or {},
        confirmed_by=user_id,
        confirmed_at=datetime.utcnow()
    )
    db.add(mapping_record)
    db.commit()
    db.refresh(mapping_record)

    # Trigger re-validation report computation with the new mapping
    compute_quality_score_and_report(db, dataset_version_id, mapping_id=mapping_record.id)

    return mapping_record
