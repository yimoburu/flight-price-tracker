from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.search import AirportResult

client = TestClient(app)


def test_airports_too_short_query() -> None:
    response = client.get("/api/v1/airports?q=LO")
    assert response.status_code == 422


def test_airports_valid_query() -> None:
    mock_results = [
        AirportResult(iata_code="LHR", name="Heathrow", city="London", country="United Kingdom"),
        AirportResult(iata_code="LGW", name="Gatwick", city="London", country="United Kingdom"),
    ]
    with patch("app.api.search.get_amadeus_client"), patch(
        "app.api.search.search_airports"
    ) as mock_search:
        mock_search.return_value = mock_results
        response = client.get("/api/v1/airports?q=LON")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["iata_code"] == "LHR"
    assert data[1]["iata_code"] == "LGW"
