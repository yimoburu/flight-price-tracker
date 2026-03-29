from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_airports_too_short_query() -> None:
    response = client.get("/api/v1/airports?q=LO")
    assert response.status_code == 422


def test_airports_valid_query() -> None:
    mock_airports = [
        {'iataCode': 'LHR', 'name': 'Heathrow', 'address': {'cityName': 'London', 'countryName': 'United Kingdom'}},
    ]
    with patch('app.api.search.get_amadeus_client') as mock_get_client, \
         patch('app.api.search.search_airports') as mock_search:
        mock_search.return_value = [__import__('app.schemas.search', fromlist=['AirportResult']).AirportResult(
            iata_code='LHR', name='Heathrow', city='London', country='United Kingdom'
        )]
        response = client.get("/api/v1/airports?q=LON")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]['iata_code'] == 'LHR'
