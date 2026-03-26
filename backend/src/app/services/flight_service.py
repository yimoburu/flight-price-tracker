from app.schemas.search import AirportResult, FlightOfferResponse, SearchRequest


def search_airports(query: str) -> list[AirportResult]:
    raise NotImplementedError


def search_flights(request: SearchRequest) -> list[FlightOfferResponse]:
    raise NotImplementedError
