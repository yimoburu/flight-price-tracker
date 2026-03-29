from amadeus import Client, Location

from app.schemas.search import AirportResult, FlightOfferResponse, SearchRequest


def search_airports(query: str, client: Client) -> list[AirportResult]:
    """Search airports and cities by keyword.

    Args:
        query: search keyword, minimum 3 characters
        client: Amadeus Client instance

    Returns:
        List of up to 10 AirportResult objects.

    Raises:
        amadeus.ResponseError: propagated to caller
    """
    response = client.reference_data.locations.get(
        keyword=query,
        subType=Location.ANY,
        **{'page[limit]': 10}
    )
    return [
        AirportResult(
            iata_code=item['iataCode'],
            name=item['name'],
            city=item.get('address', {}).get('cityName', ''),
            country=item.get('address', {}).get('countryName', ''),
        )
        for item in response.data
    ]


def search_flights(request: SearchRequest) -> list[FlightOfferResponse]:
    raise NotImplementedError
