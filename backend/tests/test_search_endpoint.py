"""Integration tests for the POST /api/v1/search endpoint — TDD for t06."""
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.search import AirportResult, FlightOfferResponse, SegmentInfo

client = TestClient(app)

today = date.today()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_ONE_WAY = {
    "origin": "JFK",
    "destination": "LHR",
    "trip_type": "one_way",
    "departure_date_from": str(today + timedelta(days=7)),
    "departure_date_to": str(today + timedelta(days=14)),
    "adults": 1,
    "max_stops": None,
}

VALID_ROUND_TRIP = {
    "origin": "JFK",
    "destination": "LHR",
    "trip_type": "round_trip",
    "departure_date_from": str(today + timedelta(days=7)),
    "departure_date_to": str(today + timedelta(days=14)),
    "return_date_from": str(today + timedelta(days=21)),
    "return_date_to": str(today + timedelta(days=28)),
    "adults": 1,
    "max_stops": None,
}


def _make_segment() -> SegmentInfo:
    return SegmentInfo(
        airline="AA",
        flight_number="AA 100",
        departure_airport="JFK",
        departure_time="2026-06-01T08:00:00",
        arrival_airport="LHR",
        arrival_time="2026-06-01T20:00:00",
        duration="PT7H",
        stops=0,
    )


def _make_offer(
    price: str = "200.00",
    departure_date: date | None = None,
    return_date: date | None = None,
    return_segments: list[SegmentInfo] | None = None,
) -> FlightOfferResponse:
    if departure_date is None:
        departure_date = today + timedelta(days=7)
    return FlightOfferResponse(
        price=price,
        currency="USD",
        departure_date=departure_date,
        return_date=return_date,
        outbound_segments=[_make_segment()],
        return_segments=return_segments or [],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_valid_one_way_search_returns_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC1: valid one_way body, mock returns 2 offers → 200 with array of 2."""
        offers = [_make_offer("200.00"), _make_offer("350.00")]
        monkeypatch.setattr(
            "app.api.search.search_flights",
            lambda req, c: offers,
        )
        monkeypatch.setattr("app.api.search.get_amadeus_client", lambda: MagicMock())

        response = client.post("/api/v1/search", json=VALID_ONE_WAY)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["price"] == "200.00"
        assert data[1]["price"] == "350.00"

    def test_valid_round_trip_search_returns_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC2: valid round_trip body, mock returns 1 offer with return_date and return_segments."""
        return_seg = SegmentInfo(
            airline="AA",
            flight_number="AA 200",
            departure_airport="LHR",
            departure_time="2026-06-21T10:00:00",
            arrival_airport="JFK",
            arrival_time="2026-06-21T13:00:00",
            duration="PT8H",
            stops=0,
        )
        offers = [
            _make_offer(
                price="500.00",
                departure_date=today + timedelta(days=7),
                return_date=today + timedelta(days=21),
                return_segments=[return_seg],
            )
        ]
        monkeypatch.setattr(
            "app.api.search.search_flights",
            lambda req, c: offers,
        )
        monkeypatch.setattr("app.api.search.get_amadeus_client", lambda: MagicMock())

        response = client.post("/api/v1/search", json=VALID_ROUND_TRIP)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["return_date"] is not None
        assert len(data[0]["return_segments"]) == 1

    def test_invalid_iata_code_returns_422(self) -> None:
        """AC3: lowercase IATA code fails validation → 422."""
        body = {**VALID_ONE_WAY, "origin": "jfk"}
        response = client.post("/api/v1/search", json=body)
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self) -> None:
        """AC4: missing departure_date_from → 422."""
        body = {k: v for k, v in VALID_ONE_WAY.items() if k != "departure_date_from"}
        response = client.post("/api/v1/search", json=body)
        assert response.status_code == 422

    def test_date_range_exceeds_30_days_returns_422(self) -> None:
        """AC5: departure window > 30 days → 422."""
        body = {
            **VALID_ONE_WAY,
            "departure_date_from": "2026-04-01",
            "departure_date_to": "2026-05-15",
        }
        response = client.post("/api/v1/search", json=body)
        assert response.status_code == 422

    def test_departure_in_past_returns_422(self) -> None:
        """AC6: departure dates in the past → 422."""
        body = {
            **VALID_ONE_WAY,
            "departure_date_from": "2020-01-01",
            "departure_date_to": "2020-01-10",
        }
        response = client.post("/api/v1/search", json=body)
        assert response.status_code == 422

    def test_service_returns_empty_list_gives_200_empty_array(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC7: mock returns [] → 200 with empty JSON array."""
        monkeypatch.setattr(
            "app.api.search.search_flights",
            lambda req, c: [],
        )
        monkeypatch.setattr("app.api.search.get_amadeus_client", lambda: MagicMock())

        response = client.post("/api/v1/search", json=VALID_ONE_WAY)

        assert response.status_code == 200
        assert response.json() == []

    def test_amadeus_rate_limit_returns_429(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC8: mock raises ResponseError with status_code=429 → 429 response."""
        from amadeus import ResponseError

        def raise_rate_limit(req, c):
            mock_response = MagicMock()
            mock_response.status_code = 429
            raise ResponseError(mock_response)

        monkeypatch.setattr("app.api.search.search_flights", raise_rate_limit)
        monkeypatch.setattr("app.api.search.get_amadeus_client", lambda: MagicMock())

        response = client.post("/api/v1/search", json=VALID_ONE_WAY)

        assert response.status_code == 429

    def test_health_endpoint_returns_200(self) -> None:
        """AC9: GET /api/v1/health returns 200 with status ok."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_airports_endpoint_returns_200_with_mock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC10: GET /api/v1/airports?q=LON returns 200 with airport array."""
        mock_results = [
            AirportResult(
                iata_code="LHR", name="Heathrow", city="London", country="United Kingdom"
            ),
            AirportResult(
                iata_code="LGW", name="Gatwick", city="London", country="United Kingdom"
            ),
        ]
        monkeypatch.setattr("app.api.search.search_airports", lambda q, c: mock_results)
        monkeypatch.setattr("app.api.search.get_amadeus_client", lambda: MagicMock())

        response = client.get("/api/v1/airports?q=LON")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["iata_code"] == "LHR"
        assert data[1]["iata_code"] == "LGW"
