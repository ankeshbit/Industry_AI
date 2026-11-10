"""
Machine Registry Tests (PRD v1.2 §8.2, §13.3, AC-MM-1..3, AC-PLAT-3)
"""

import pytest
from sqlalchemy import inspect
from backend.app.models.machine import Machine

def test_machine_creation_defaults_to_default_plant(client, tenant_fixture):
    """AC-MM-1: Machine creation defaults to the organisation's default plant."""
    payload = {
        "asset_tag": "MILL-042",
        "name": "5-Axis CNC Milling Center",
        "category_code": "GENERAL_MACHINE_TOOL",
        "manufacturer": "Haas",
        "model_number": "VF-2SS"
    }
    resp = client.post("/api/v1/machines", json=payload, headers=tenant_fixture["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["asset_tag"] == "MILL-042"
    assert data["plant_id"] == tenant_fixture["plant"].id

def test_duplicate_asset_tag_within_org_returns_409(client, tenant_fixture):
    """AC-MM-1: Duplicate asset tag within an organisation returns 409 DUPLICATE_ASSET_TAG."""
    payload = {
        "asset_tag": "LATHE-001",
        "name": "Lathe Alpha",
        "category_code": "GENERAL_MACHINE_TOOL"
    }
    resp1 = client.post("/api/v1/machines", json=payload, headers=tenant_fixture["headers"])
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/machines", json=payload, headers=tenant_fixture["headers"])
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "DUPLICATE_ASSET_TAG"

def test_same_asset_tag_across_different_orgs_succeeds(client, two_tenants_fixture):
    """AC-MM-1: The same asset tag in another organisation is permitted."""
    payload = {
        "asset_tag": "SHARED-TAG-99",
        "name": "Standard Machine",
        "category_code": "GENERAL_MACHINE_TOOL"
    }
    t1 = two_tenants_fixture["tenant1"]
    t2 = two_tenants_fixture["tenant2"]

    # Org 1 creates with tag
    resp1 = client.post("/api/v1/machines", json=payload, headers=t1["headers"])
    assert resp1.status_code == 201

    # Org 2 creates with exact same tag
    resp2 = client.post("/api/v1/machines", json=payload, headers=t2["headers"])
    assert resp2.status_code == 201
    assert resp1.json()["id"] != resp2.json()["id"]

def test_archived_machine_rejects_new_dataset_and_remains_readable(client, tenant_fixture):
    """AC-MM-2: Archived machines reject new datasets with 409 and remain readable."""
    # 1. Create machine
    m_resp = client.post("/api/v1/machines", json={
        "asset_tag": "PRESS-007",
        "name": "Hydraulic Stamping Press",
        "category_code": "GENERAL_MACHINE_TOOL"
    }, headers=tenant_fixture["headers"])
    machine_id = m_resp.json()["id"]

    # 2. Archive machine
    arch_resp = client.post(f"/api/v1/machines/{machine_id}/archive", headers=tenant_fixture["headers"])
    assert arch_resp.status_code == 200

    # 3. Machine remains readable
    read_resp = client.get(f"/api/v1/machines/{machine_id}", headers=tenant_fixture["headers"])
    assert read_resp.status_code == 200
    assert read_resp.json()["archived_at"] is not None

    # 4. Creating a dataset for this archived machine returns 409 MACHINE_ARCHIVED
    ds_resp = client.post(f"/api/v1/machines/{machine_id}/datasets", json={
        "name": "Run Data After Archive"
    }, headers=tenant_fixture["headers"])
    assert ds_resp.status_code == 409
    assert ds_resp.json()["error"]["code"] == "MACHINE_ARCHIVED"

def test_no_hardware_or_iot_fields_in_machine_schema(db_session):
    """AC-MM-3 & AC-PLAT-3: No schema field refers to devices, hardware sensors, protocols (MQTT, ESP32, Arduino)."""
    inspector = inspect(db_session.bind)
    cols = [c["name"].lower() for c in inspector.get_columns("machines")]

    forbidden_hardware_words = [
        "device", "sensor", "mqtt", "telemetry", "hardware", "esp32", "arduino", "protocol", "port", "ip_address", "firmware"
    ]
    for col in cols:
        for word in forbidden_hardware_words:
            assert word not in col, f"Forbidden IoT/hardware field '{col}' found on machines table!"

def test_machine_categories_endpoint(client):
    """PRD §8.2.2: Machine categories endpoint returns supported categories."""
    resp = client.get("/api/v1/machine-categories")
    assert resp.status_code == 200
    categories = resp.json()
    codes = [c["code"] for c in categories]
    assert "GENERAL_MACHINE_TOOL" in codes
    assert "TURBOFAN_ENGINE" in codes
    assert "BEARING_ROTATING" in codes
    assert "ACOUSTIC_MACHINE" in codes
    assert "OTHER" in codes

