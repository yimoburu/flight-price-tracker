from pydantic import BaseModel


class AirportResult(BaseModel):
    iata_code: str
    name: str
    city: str
    country: str


class SegmentInfo(BaseModel):
    airline: str
    flight_number: str
    departure_airport: str
    departure_time: str
    arrival_airport: str
    arrival_time: str
    duration: str
    stops: int


class FlightOfferResponse(BaseModel):
    price: str
    currency: str
    departure_date: str
    return_date: str | None
    outbound_segments: list[SegmentInfo]
    return_segments: list[SegmentInfo]


class SearchRequest(BaseModel):
    origin: str
    destination: str
    trip_type: str
    departure_date_from: str
    departure_date_to: str
    return_date_from: str = ""
    return_date_to: str = ""
    adults: int = 1
    max_stops: int | None = None
