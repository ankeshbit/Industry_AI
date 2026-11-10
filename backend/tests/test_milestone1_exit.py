"""
Milestone 1 Authoritative Acceptance Exit Test (PRD v1.2 §18.3, lines 2621-2622)

Exact Sequence:
1. Register an organisation
2. Attempt to register a second (refused, MULTI_ORG_DISABLED)
3. Create a machine
4. Upload an AI4I-schema CSV with renamed columns and Celsius temperatures and no Type column
5. Wizard maps and sets units
6. Only NO_TYPE is offered (WITH_TYPE is INCOMPATIBLE due to missing product_type)
7. Acknowledge warnings and the reference model limitation
8. Run failure prediction analysis
9. View stored result with provenance and trust fields
10. Upload a CSV missing torque and verify refusal with remedies
11. Upload a CSV containing a Type column and verify both configurations are offered separately
"""

import io
import pytest
from backend.app.config import settings

def test_milestone_1_authoritative_exit_test(client):
    settings.MULTI_ORG_ENABLED = False

    # -------------------------------------------------------------------------
    # STEP 1: Register an organisation
    # -------------------------------------------------------------------------
    reg_payload = {
        "organisation_name": "Vanguard Precision Machining",
        "email": "director@vanguardmachining.com",
        "full_name": "Elena Rostova",
        "password": "SecureEnterprisePassword2026!"
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    assert reg_resp.json()["status"] == "ACTIVE"

    # Log in as Org Admin
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "director@vanguardmachining.com",
        "password": "SecureEnterprisePassword2026!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # -------------------------------------------------------------------------
    # STEP 2: Attempt to register a second organisation (refused, MULTI_ORG_DISABLED)
    # -------------------------------------------------------------------------
    second_org_payload = {
        "organisation_name": "Rival Machining Corp",
        "email": "rival@rivalmachining.com",
        "full_name": "Bob Rival",
        "password": "SecondPassword2026!"
    }
    second_resp = client.post("/api/v1/auth/register", json=second_org_payload)
    assert second_resp.status_code == 403
    assert second_resp.json()["error"]["code"] == "MULTI_ORG_DISABLED"

    # -------------------------------------------------------------------------
    # STEP 3: Create a machine
    # -------------------------------------------------------------------------
    mach_resp = client.post("/api/v1/machines", json={
        "asset_tag": "CNC-MILL-501",
        "name": "5-Axis High Precision CNC Mill",
        "category_code": "GENERAL_MACHINE_TOOL",
        "manufacturer": "Matsuura",
        "model_number": "MX-520"
    }, headers=headers)
    assert mach_resp.status_code == 201
    machine_id = mach_resp.json()["id"]

    # -------------------------------------------------------------------------
    # STEP 4: Upload an AI4I-schema CSV with renamed columns and Celsius temperatures and NO Type column
    # -------------------------------------------------------------------------
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Line 1 Daily Operating Batch",
        "dataset_type": "TABULAR_OPERATING_STATE"
    }, headers=headers)
    assert ds_resp.status_code == 201
    dataset_id = ds_resp.json()["id"]

    # Renamed columns, Celsius temperatures (~25C = ~298K, ~35C = ~308K in reference range), no Type column
    celsius_no_type_csv = (
        "Ambient Temp [C],Process Chamber Temp [C],Spindle RPM,Drive Torque [Nm],Cumulative Tool Wear [min]\n"
        "25.0,35.5,1550,42.5,15\n"
        "25.2,35.7,1480,45.1,18\n"
        "24.9,35.3,1510,40.8,22\n"
        "25.1,35.6,1430,46.0,26\n"
        "25.3,35.8,1405,48.2,30\n"
    )
    files = {"file": ("batch_operating_data.csv", io.BytesIO(celsius_no_type_csv.encode("utf-8")), "text/csv")}
    upload_resp = client.post(f"/api/v1/datasets/{dataset_id}/versions/upload", files=files, headers=headers)
    assert upload_resp.status_code == 201
    vid1 = upload_resp.json()["dataset_version_id"]
    assert upload_resp.json()["row_count"] == 5

    # -------------------------------------------------------------------------
    # STEP 5: Wizard maps and sets units
    # -------------------------------------------------------------------------
    # Mapping for ai4i_failure_no_type
    mapping_payload = {
        "mappings": {
            "air_temperature": {"column": "Ambient Temp [C]", "unit": "degC"},
            "process_temperature": {"column": "Process Chamber Temp [C]", "unit": "degC"},
            "rotational_speed": {"column": "Spindle RPM", "unit": "rpm"},
            "torque": {"column": "Drive Torque [Nm]", "unit": "Nm"},
            "tool_wear": {"column": "Cumulative Tool Wear [min]", "unit": "min"}
        }
    }
    map_resp = client.put(f"/api/v1/dataset-versions/{vid1}/mappings/ai4i_failure_no_type", json=mapping_payload, headers=headers)
    assert map_resp.status_code == 200

    # -------------------------------------------------------------------------
    # STEP 6: Only NO_TYPE is offered (evaluating both profiles)
    # -------------------------------------------------------------------------
    # When requesting compatibility check without profile_id, evaluates all eligible profiles
    checks_resp = client.post(f"/api/v1/dataset-versions/{vid1}/compatibility-checks", json={}, headers=headers)
    assert checks_resp.status_code == 201
    checks = checks_resp.json()
    assert len(checks) == 2

    no_type_check = next(c for c in checks if c["profile"]["configuration"] == "NO_TYPE")
    with_type_check = next(c for c in checks if c["profile"]["configuration"] == "WITH_TYPE")

    # NO_TYPE is COMPATIBLE
    assert no_type_check["compatibility"]["status"] == "COMPATIBLE"
    assert no_type_check["applicability"]["level"] == "IN_REFERENCE_RANGE"
    assert no_type_check["reliability"]["tier"] == "REFERENCE_ONLY"

    # WITH_TYPE is INCOMPATIBLE because product_type is missing
    assert with_type_check["compatibility"]["status"] == "INCOMPATIBLE"
    reasons_with_type = [r["code"] for r in with_type_check["compatibility"]["reasons"]]
    assert "E_MISSING_FEATURE" in reasons_with_type

    # -------------------------------------------------------------------------
    # STEP 7: Acknowledge warnings and the reference model limitation
    # -------------------------------------------------------------------------
    # In this clean in-range dataset, requires_acknowledgement is empty or contains minor warnings
    active_warnings = no_type_check["requires_acknowledgement"]
    limitation_ack = True

    # -------------------------------------------------------------------------
    # STEP 8: Run failure prediction analysis
    # -------------------------------------------------------------------------
    run_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": no_type_check["id"],
        "acknowledged_reason_codes": active_warnings,
        "limitation_acknowledged": limitation_ack
    }, headers=headers)
    assert run_resp.status_code == 202
    result_id = run_resp.json()["analysis_result_id"]
    assert result_id is not None

    # -------------------------------------------------------------------------
    # STEP 9: View stored result with provenance and trust fields
    # -------------------------------------------------------------------------
    res_resp = client.get(f"/api/v1/analyses/{result_id}", headers=headers)
    assert res_resp.status_code == 200
    res = res_resp.json()

    # Provenance fields
    assert res["configuration"] == "NO_TYPE"
    assert res["provenance"]["model"]["registry_name"] == "ai4i_failure_clf_notype"
    assert res["provenance"]["model"]["training_domain"] == "REFERENCE_DATASET"
    assert "AI4I 2020" in res["provenance"]["model"]["trained_on"]

    # Trust Panel fields
    assert res["trust"]["reliability_tier"] == "REFERENCE_ONLY"
    assert "not validated on your equipment" in res["trust"]["label"]
    assert res["semantics"] == "Reference-calibrated failure probability for the supplied operating state; no time horizon is implied."
    assert res["evaluation_sections"]["customer_specific_validation"] is None
    assert len(res["limitations"]) > 0

    # Predictions
    assert res["summary"]["total_rows"] == 5
    assert "failure_rate" in res["summary"]

    # -------------------------------------------------------------------------
    # STEP 10: Upload a CSV missing torque and verify refusal with remedies
    # -------------------------------------------------------------------------
    ds2_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Dataset Missing Torque"
    }, headers=headers)
    dataset2_id = ds2_resp.json()["id"]

    missing_torque_csv = (
        "Air temp,Process temp,RPM,Tool wear\n"
        "298.1,308.6,1550,15\n"
        "298.2,308.7,1480,18\n"
    )
    files_no_torque = {"file": ("missing_torque.csv", io.BytesIO(missing_torque_csv.encode("utf-8")), "text/csv")}
    up2_resp = client.post(f"/api/v1/datasets/{dataset2_id}/versions/upload", files=files_no_torque, headers=headers)
    vid2 = up2_resp.json()["dataset_version_id"]

    # Map only available features (torque cannot be mapped)
    partial_mapping = {
        "mappings": {
            "air_temperature": {"column": "Air temp", "unit": "K"},
            "process_temperature": {"column": "Process temp", "unit": "K"},
            "rotational_speed": {"column": "RPM", "unit": "rpm"},
            "tool_wear": {"column": "Tool wear", "unit": "min"}
        }
    }
    client.put(f"/api/v1/dataset-versions/{vid2}/mappings/ai4i_failure_no_type", json=partial_mapping, headers=headers)

    # Check compatibility
    chk2_resp = client.post(f"/api/v1/dataset-versions/{vid2}/compatibility-checks", json={"profile_id": "ai4i_failure_no_type"}, headers=headers)
    chk2 = chk2_resp.json()[0]
    assert chk2["compatibility"]["status"] == "INCOMPATIBLE"

    # Verify remedy text for missing torque
    torque_reason = next(r for r in chk2["compatibility"]["reasons"] if r.get("feature") == "torque")
    assert torque_reason["code"] == "E_MISSING_FEATURE"
    assert "remedy" in torque_reason
    assert "Map a dataset column to canonical feature 'torque'" in torque_reason["remedy"]

    # Verify refusal to run analysis
    run_refused_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": chk2["id"],
        "limitation_acknowledged": True
    }, headers=headers)
    assert run_refused_resp.status_code == 422
    assert run_refused_resp.json()["error"]["code"] == "INCOMPATIBLE"

    # -------------------------------------------------------------------------
    # STEP 11: Upload a CSV containing a Type column and verify both configurations are offered separately
    # -------------------------------------------------------------------------
    ds3_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Dataset With Type Column"
    }, headers=headers)
    dataset3_id = ds3_resp.json()["id"]

    typed_csv = (
        "Type,Air temp,Process temp,RPM,Torque,Tool wear\n"
        "M,298.1,308.6,1550,42.5,15\n"
        "L,298.2,308.7,1480,45.1,18\n"
        "H,298.0,308.4,1510,40.8,22\n"
        "M,298.3,308.8,1430,46.0,26\n"
        "L,298.4,308.9,1405,48.2,30\n"
    )
    files_typed = {"file": ("typed_operating_data.csv", io.BytesIO(typed_csv.encode("utf-8")), "text/csv")}
    up3_resp = client.post(f"/api/v1/datasets/{dataset3_id}/versions/upload", files=files_typed, headers=headers)
    vid3 = up3_resp.json()["dataset_version_id"]

    # Map for NO_TYPE
    mapping_no_type = {
        "mappings": {
            "air_temperature": {"column": "Air temp", "unit": "K"},
            "process_temperature": {"column": "Process temp", "unit": "K"},
            "rotational_speed": {"column": "RPM", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Tool wear", "unit": "min"}
        }
    }
    client.put(f"/api/v1/dataset-versions/{vid3}/mappings/ai4i_failure_no_type", json=mapping_no_type, headers=headers)

    # Map for WITH_TYPE (including product_type with asserted_equivalence=true)
    mapping_with_type = {
        "mappings": {
            "air_temperature": {"column": "Air temp", "unit": "K"},
            "process_temperature": {"column": "Process temp", "unit": "K"},
            "rotational_speed": {"column": "RPM", "unit": "rpm"},
            "torque": {"column": "Torque", "unit": "Nm"},
            "tool_wear": {"column": "Tool wear", "unit": "min"},
            "product_type": {"column": "Type", "asserted_equivalence": True}
        }
    }
    client.put(f"/api/v1/dataset-versions/{vid3}/mappings/ai4i_failure_with_type", json=mapping_with_type, headers=headers)

    # Evaluate compatibility for all eligible profiles
    checks3_resp = client.post(f"/api/v1/dataset-versions/{vid3}/compatibility-checks", json={}, headers=headers)
    assert checks3_resp.status_code == 201
    checks3 = checks3_resp.json()

    c_no_type = next(c for c in checks3 if c["profile"]["configuration"] == "NO_TYPE")
    c_with_type = next(c for c in checks3 if c["profile"]["configuration"] == "WITH_TYPE")

    # BOTH configurations are runnable!
    assert c_no_type["compatibility"]["status"] in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS")
    assert c_with_type["compatibility"]["status"] in ("COMPATIBLE", "COMPATIBLE_WITH_WARNINGS")

    # Both are offered separately; results are stored separately
    run_typed_resp = client.post("/api/v1/analyses", json={
        "compatibility_check_id": c_with_type["id"],
        "acknowledged_reason_codes": c_with_type["requires_acknowledgement"],
        "limitation_acknowledged": True
    }, headers=headers)
    assert run_typed_resp.status_code == 202
    typed_result_id = run_typed_resp.json()["analysis_result_id"]

    res_typed = client.get(f"/api/v1/analyses/{typed_result_id}", headers=headers).json()
    assert res_typed["configuration"] == "WITH_TYPE"
    assert res_typed["provenance"]["model"]["registry_name"] == "ai4i_failure_clf_typed"
    assert res_typed["trust"]["reliability_tier"] == "REFERENCE_ONLY"
