"""Tests for tracking Pydantic schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.tracking import (
    CreateTrackedSearchRequest,
    PriceHistoryResponse,
    PriceSnapshotResponse,
    TrackedSearchResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CREATE = dict(
    origin="JFK",
    destination="LAX",
    trip_type="one_way",
    departure_date_from=date(2026, 6, 1),
    departure_date_to=date(2026, 6, 10),
    adults=1,
    threshold_price=Decimal("200.00"),
    alert_email="user@example.com",
)


def make_create(**overrides):
    return {**VALID_CREATE, **overrides}


# ---------------------------------------------------------------------------
# CreateTrackedSearchRequest
# ---------------------------------------------------------------------------


class TestCreateTrackedSearchRequest:
    def test_valid_data(self):
        req = CreateTrackedSearchRequest(**VALID_CREATE)
        assert req.origin == "JFK"
        assert req.destination == "LAX"
        assert req.trip_type == "one_way"
        assert req.threshold_price == Decimal("200.00")
        assert req.alert_email == "user@example.com"

    # origin / destination length validation
    def test_origin_too_short(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(origin="JF"))

    def test_origin_too_long(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(origin="JFKX"))

    def test_destination_too_short(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(destination="LA"))

    def test_destination_too_long(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(destination="LAXX"))

    # trip_type validation
    def test_trip_type_one_way_valid(self):
        req = CreateTrackedSearchRequest(**make_create(trip_type="one_way"))
        assert req.trip_type == "one_way"

    def test_trip_type_round_trip_valid(self):
        req = CreateTrackedSearchRequest(**make_create(trip_type="round_trip"))
        assert req.trip_type == "round_trip"

    def test_trip_type_invalid(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(trip_type="multi_city"))

    # threshold_price validation
    def test_threshold_price_zero_invalid(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(threshold_price=Decimal("0")))

    def test_threshold_price_negative_invalid(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(threshold_price=Decimal("-1.00")))

    def test_threshold_price_positive_valid(self):
        req = CreateTrackedSearchRequest(**make_create(threshold_price=Decimal("0.01")))
        assert req.threshold_price == Decimal("0.01")

    # alert_email validation
    def test_alert_email_invalid(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(alert_email="not-an-email"))

    def test_alert_email_valid(self):
        req = CreateTrackedSearchRequest(**make_create(alert_email="test@domain.org"))
        assert req.alert_email == "test@domain.org"

    # adults validation
    def test_adults_default_is_1(self):
        data = {k: v for k, v in VALID_CREATE.items() if k != "adults"}
        req = CreateTrackedSearchRequest(**data)
        assert req.adults == 1

    def test_adults_zero_invalid(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(adults=0))

    def test_adults_valid(self):
        req = CreateTrackedSearchRequest(**make_create(adults=3))
        assert req.adults == 3

    # max_stops validation
    def test_max_stops_default_is_none(self):
        req = CreateTrackedSearchRequest(**VALID_CREATE)
        assert req.max_stops is None

    def test_max_stops_negative_invalid(self):
        with pytest.raises(ValidationError):
            CreateTrackedSearchRequest(**make_create(max_stops=-1))

    def test_max_stops_zero_valid(self):
        req = CreateTrackedSearchRequest(**make_create(max_stops=0))
        assert req.max_stops == 0

    # optional return dates
    def test_return_dates_are_optional(self):
        req = CreateTrackedSearchRequest(**VALID_CREATE)
        assert req.return_date_from is None
        assert req.return_date_to is None

    def test_return_dates_can_be_set(self):
        req = CreateTrackedSearchRequest(
            **make_create(
                return_date_from=date(2026, 6, 20),
                return_date_to=date(2026, 6, 25),
            )
        )
        assert req.return_date_from == date(2026, 6, 20)
        assert req.return_date_to == date(2026, 6, 25)


# ---------------------------------------------------------------------------
# TrackedSearchResponse
# ---------------------------------------------------------------------------

VALID_RESPONSE = dict(
    id="abc123",
    client_id="client-xyz",
    origin="JFK",
    destination="LAX",
    trip_type="one_way",
    departure_date_from=date(2026, 6, 1),
    departure_date_to=date(2026, 6, 10),
    return_date_from=None,
    return_date_to=None,
    adults=1,
    max_stops=None,
    threshold_price=Decimal("200.00"),
    alert_email="user@example.com",
    created_at=datetime(2026, 3, 1, 12, 0, 0),
    is_active=True,
    current_best_price=None,
    last_checked_at=None,
)


class TestTrackedSearchResponse:
    def test_construct_from_dict(self):
        resp = TrackedSearchResponse(**VALID_RESPONSE)
        assert resp.id == "abc123"
        assert resp.client_id == "client-xyz"
        assert resp.is_active is True
        assert resp.current_best_price is None

    def test_from_attributes_config(self):
        # Verify model_config from_attributes is True by checking model construction
        assert TrackedSearchResponse.model_config.get("from_attributes") is True

    def test_with_best_price(self):
        data = {**VALID_RESPONSE, "current_best_price": Decimal("150.00")}
        resp = TrackedSearchResponse(**data)
        assert resp.current_best_price == Decimal("150.00")

    def test_with_last_checked_at(self):
        ts = datetime(2026, 3, 28, 10, 0, 0)
        data = {**VALID_RESPONSE, "last_checked_at": ts}
        resp = TrackedSearchResponse(**data)
        assert resp.last_checked_at == ts


# ---------------------------------------------------------------------------
# PriceHistoryResponse
# ---------------------------------------------------------------------------


class TestPriceHistoryResponse:
    def test_empty_snapshots_is_valid(self):
        resp = PriceHistoryResponse(tracked_search_id="abc123", snapshots=[])
        assert resp.tracked_search_id == "abc123"
        assert resp.snapshots == []

    def test_with_snapshots(self):
        snap = PriceSnapshotResponse(
            checked_at=datetime(2026, 3, 28, 8, 0, 0),
            best_price=Decimal("199.99"),
            currency="USD",
        )
        resp = PriceHistoryResponse(tracked_search_id="abc123", snapshots=[snap])
        assert len(resp.snapshots) == 1
        assert resp.snapshots[0].best_price == Decimal("199.99")

    def test_price_snapshot_from_attributes_config(self):
        assert PriceSnapshotResponse.model_config.get("from_attributes") is True
