import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class SearchRequest(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    trip_type: Literal["one_way", "round_trip"]
    departure_date_from: date
    departure_date_to: date
    return_date_from: date | None = None
    return_date_to: date | None = None
    adults: int = Field(default=1, ge=1, le=9)
    max_stops: int | None = Field(default=None, ge=0, le=2)

    @field_validator("origin", "destination")
    @classmethod
    def must_be_iata(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{3}$", v):
            raise ValueError("must be exactly 3 uppercase ASCII letters")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "SearchRequest":
        today = date.today()
        if self.departure_date_from < today:
            raise ValueError("departure_date_from must not be in the past")
        if self.departure_date_to < self.departure_date_from:
            raise ValueError("departure_date_to must be >= departure_date_from")
        if (self.departure_date_to - self.departure_date_from).days > 30:
            raise ValueError("departure date range must not exceed 30 days")
        if self.trip_type == "round_trip":
            if self.return_date_from is None or self.return_date_to is None:
                raise ValueError("return_date_from and return_date_to are required for round_trip")
            if self.return_date_from < self.departure_date_from:
                raise ValueError("return_date_from must be >= departure_date_from")
            if (self.return_date_to - self.return_date_from).days > 30:
                raise ValueError("return date range must not exceed 30 days")
        return self


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
    departure_date: date
    return_date: date | None = None
    outbound_segments: list[SegmentInfo]
    return_segments: list[SegmentInfo] = []


class AirportResult(BaseModel):
    iata_code: str
    name: str
    city: str
    country: str
