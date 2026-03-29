from unittest.mock import MagicMock
from app.services.flight_service import search_airports


def test_search_airports_returns_results() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [
        {'iataCode': 'LHR', 'name': 'Heathrow', 'address': {'cityName': 'London', 'countryName': 'United Kingdom'}},
        {'iataCode': 'LGW', 'name': 'Gatwick', 'address': {'cityName': 'London', 'countryName': 'United Kingdom'}},
    ]
    mock_client.reference_data.locations.get.return_value = mock_response
    results = search_airports('LON', mock_client)
    assert len(results) == 2
    assert results[0].iata_code == 'LHR'
    assert results[0].name == 'Heathrow'
    assert results[0].city == 'London'
    assert results[0].country == 'United Kingdom'


def test_search_airports_empty_response() -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = []
    mock_client.reference_data.locations.get.return_value = mock_response
    results = search_airports('XYZ', mock_client)
    assert results == []
