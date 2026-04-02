from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from app.db import Base, get_db
from app.main import app
from app.models.tracked_search import PriceSnapshot

TEST_DB_URL = "sqlite:///file:test_tracking_api?mode=memory&cache=shared&uri=true"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=test_engine)

CLIENT_UUID = "12345678-1234-4234-8234-123456789abc"
OTHER_UUID = "87654321-4321-4321-8321-987654321cba"

VALID_BODY = {
    "origin": "JFK",
    "destination": "LAX",
    "trip_type": "one_way",
    "departure_date_from": "2026-04-01",
    "departure_date_to": "2026-04-07",
    "adults": 1,
    "threshold_price": "300.00",
    "alert_email": "user@example.com",
}


@pytest.fixture(autouse=True)
def db_session():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# Test 1: POST creates a tracked search and returns 201 with expected fields
def test_create_tracked_search_success(client: TestClient):
    response = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["origin"] == "JFK"
    assert data["destination"] == "LAX"
    assert data["client_id"] == CLIENT_UUID
    assert data["current_best_price"] is None
    assert data["last_checked_at"] is None


# Test 2: POST without X-Client-ID header → 422
def test_create_tracked_search_missing_client_id(client: TestClient):
    response = client.post("/api/v1/tracked-searches", json=VALID_BODY)
    assert response.status_code == 422


# Test 3: POST with invalid UUID → 400, detail mentions UUID
def test_create_tracked_search_invalid_client_id(client: TestClient):
    response = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": "not-a-valid-uuid"},
    )
    assert response.status_code == 400
    assert "UUID" in response.json()["detail"]


# Test 4: POST with invalid email → 422
def test_create_tracked_search_invalid_email(client: TestClient):
    body = {**VALID_BODY, "alert_email": "not-an-email"}
    response = client.post(
        "/api/v1/tracked-searches",
        json=body,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 422


# Test 5: POST with threshold_price of 0 → 422
def test_create_tracked_search_threshold_zero(client: TestClient):
    body = {**VALID_BODY, "threshold_price": "0"}
    response = client.post(
        "/api/v1/tracked-searches",
        json=body,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 422


# Test 6: POST with threshold_price negative → 422
def test_create_tracked_search_threshold_negative(client: TestClient):
    body = {**VALID_BODY, "threshold_price": "-50.00"}
    response = client.post(
        "/api/v1/tracked-searches",
        json=body,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 422


# Test 7: GET returns only rows for this client_id
def test_list_tracked_searches_client_isolation(client: TestClient):
    # Create one for our client
    client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    # Create one for another client
    client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": OTHER_UUID},
    )
    response = client.get(
        "/api/v1/tracked-searches",
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["client_id"] == CLIENT_UUID


# Test 8: GET returns current_best_price and last_checked_at from latest PriceSnapshot
def test_list_tracked_searches_with_snapshot(client: TestClient):
    create_resp = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    search_id = create_resp.json()["id"]

    # Manually insert a snapshot via the DB override
    db = TestingSession()
    checked_at = datetime(2026, 4, 10, 12, 0, 0)
    snapshot = PriceSnapshot(
        tracked_search_id=search_id,
        checked_at=checked_at,
        best_price=Decimal("250.00"),
        currency="USD",
    )
    db.add(snapshot)
    db.commit()
    db.close()

    response = client.get(
        "/api/v1/tracked-searches",
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["current_best_price"] == "250.00"
    assert data[0]["last_checked_at"] is not None


# Test 9: DELETE returns 204; subsequent GET does not include it
def test_delete_tracked_search_success(client: TestClient):
    create_resp = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    search_id = create_resp.json()["id"]

    del_resp = client.delete(
        f"/api/v1/tracked-searches/{search_id}",
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert del_resp.status_code == 204

    list_resp = client.get(
        "/api/v1/tracked-searches",
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert search_id not in ids


# Test 10: DELETE on unknown id → 404
def test_delete_tracked_search_not_found(client: TestClient):
    response = client.delete(
        "/api/v1/tracked-searches/nonexistent-id",
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 404


# Test 11: DELETE with wrong client_id → 404
def test_delete_tracked_search_wrong_client(client: TestClient):
    create_resp = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    search_id = create_resp.json()["id"]

    response = client.delete(
        f"/api/v1/tracked-searches/{search_id}",
        headers={"X-Client-ID": OTHER_UUID},
    )
    assert response.status_code == 404


# Test 12: GET history returns snapshots ordered oldest to newest
def test_get_price_history_ordered(client: TestClient):
    create_resp = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    search_id = create_resp.json()["id"]

    db = TestingSession()
    snapshots = [
        PriceSnapshot(
            tracked_search_id=search_id,
            checked_at=datetime(2026, 4, 10, 12, 0, 0),
            best_price=Decimal("300.00"),
            currency="USD",
        ),
        PriceSnapshot(
            tracked_search_id=search_id,
            checked_at=datetime(2026, 4, 8, 10, 0, 0),
            best_price=Decimal("280.00"),
            currency="USD",
        ),
        PriceSnapshot(
            tracked_search_id=search_id,
            checked_at=datetime(2026, 4, 9, 11, 0, 0),
            best_price=Decimal("290.00"),
            currency="USD",
        ),
    ]
    db.add_all(snapshots)
    db.commit()
    db.close()

    response = client.get(
        f"/api/v1/tracked-searches/{search_id}/history",
        headers={"X-Client-ID": CLIENT_UUID},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tracked_search_id"] == search_id
    prices = [s["best_price"] for s in data["snapshots"]]
    # Should be oldest to newest: 280, 290, 300
    assert prices == ["280.00", "290.00", "300.00"]


# Test 13: GET history with wrong client_id → 404
def test_get_price_history_wrong_client(client: TestClient):
    create_resp = client.post(
        "/api/v1/tracked-searches",
        json=VALID_BODY,
        headers={"X-Client-ID": CLIENT_UUID},
    )
    search_id = create_resp.json()["id"]

    response = client.get(
        f"/api/v1/tracked-searches/{search_id}/history",
        headers={"X-Client-ID": OTHER_UUID},
    )
    assert response.status_code == 404
