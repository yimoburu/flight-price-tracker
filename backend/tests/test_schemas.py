"""Tests for Pydantic v2 schemas in app.schemas.search."""
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.search import (
    AirportResult,
    FlightOfferResponse,
    SearchRequest,
    SegmentInfo,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_one_way(**overrides) -> dict:
    """Return a minimal valid one-way SearchRequest dict."""
    base = {
        "origin": "JFK",
        "destination": "LAX",
        "trip_type": "one_way",
        "departure_date_from": "2026-04-01",
        "departure_date_to": "2026-04-15",
        "adults": 1,
    }
    base.update(overrides)
    return base


def _valid_round_trip(**overrides) -> dict:
    """Return a minimal valid round-trip SearchRequest dict."""
    base = {
        "origin": "JFK",
        "destination": "LAX",
        "trip_type": "round_trip",
        "departure_date_from": "2026-04-01",
        "departure_date_to": "2026-04-15",
        "return_date_from": "2026-04-20",
        "return_date_to": "2026-04-30",
        "adults": 1,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test 1 — Valid SearchRequest parses correctly
# ---------------------------------------------------------------------------

def test_valid_search_request_parses() -> None:
    req = SearchRequest(**_valid_one_way(adults=2))
    assert req.origin == "JFK"
    assert req.adults == 2


# ---------------------------------------------------------------------------
# Test 2 — IATA lowercase rejects
# ---------------------------------------------------------------------------

def test_iata_lowercase_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_one_way(origin="jfk"))


# ---------------------------------------------------------------------------
# Test 3 — IATA 4-letter code rejects (max_length=3)
# ---------------------------------------------------------------------------

def test_iata_four_letter_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_one_way(origin="KJFK"))


# ---------------------------------------------------------------------------
# Test 4 — Departure in the past rejects
# ---------------------------------------------------------------------------

def test_departure_in_past_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_one_way(
            departure_date_from="2020-01-01",
            departure_date_to="2020-01-10",
        ))


# ---------------------------------------------------------------------------
# Test 5 — Date range > 30 days rejects
# ---------------------------------------------------------------------------

def test_departure_range_over_30_days_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_one_way(
            departure_date_from="2026-04-01",
            departure_date_to="2026-05-15",
        ))


# ---------------------------------------------------------------------------
# Test 6 — Round-trip missing return dates rejects
# ---------------------------------------------------------------------------

def test_round_trip_missing_return_dates_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_round_trip(
            return_date_from=None,
            return_date_to=None,
        ))


# ---------------------------------------------------------------------------
# Test 7 — Round-trip return range > 30 days rejects
# ---------------------------------------------------------------------------

def test_round_trip_return_range_over_30_days_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_round_trip(
            return_date_from="2026-04-01",
            return_date_to="2026-05-15",
        ))


# ---------------------------------------------------------------------------
# Test 8 — max_stops=None passes
# ---------------------------------------------------------------------------

def test_max_stops_none_passes() -> None:
    req = SearchRequest(**_valid_one_way(max_stops=None))
    assert req.max_stops is None


# ---------------------------------------------------------------------------
# Test 9 — max_stops=-1 rejects
# ---------------------------------------------------------------------------

def test_max_stops_negative_rejects() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**_valid_one_way(max_stops=-1))


# ---------------------------------------------------------------------------
# Additional structural tests for response schemas
# ---------------------------------------------------------------------------

def test_segment_info_parses() -> None:
    seg = SegmentInfo(
        airline="BA",
        flight_number="BA 123",
        departure_airport="LHR",
        departure_time="2026-04-01T10:00:00",
        arrival_airport="JFK",
        arrival_time="2026-04-01T13:00:00",
        duration="PT7H",
        stops=0,
    )
    assert seg.airline == "BA"
    assert seg.stops == 0


def test_flight_offer_response_parses() -> None:
    seg = SegmentInfo(
        airline="BA",
        flight_number="BA 123",
        departure_airport="LHR",
        departure_time="2026-04-01T10:00:00",
        arrival_airport="JFK",
        arrival_time="2026-04-01T13:00:00",
        duration="PT7H",
        stops=0,
    )
    offer = FlightOfferResponse(
        price="298.50",
        currency="USD",
        departure_date=date(2026, 4, 1),
        return_date=None,
        outbound_segments=[seg],
    )
    assert offer.price == "298.50"
    assert offer.return_segments == []


def test_airport_result_parses() -> None:
    airport = AirportResult(
        iata_code="JFK",
        name="John F. Kennedy International Airport",
        city="New York",
        country="US",
    )
    assert airport.iata_code == "JFK"
