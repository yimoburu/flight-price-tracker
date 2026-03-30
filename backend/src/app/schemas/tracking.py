from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class CreateTrackedSearchRequest(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    trip_type: str = Field(..., pattern="^(one_way|round_trip)$")
    departure_date_from: date
    departure_date_to: date
    return_date_from: Optional[date] = None
    return_date_to: Optional[date] = None
    adults: int = Field(default=1, ge=1, le=9)
    max_stops: Optional[int] = Field(default=None, ge=0)
    threshold_price: Decimal = Field(..., gt=0)
    alert_email: EmailStr


class TrackedSearchResponse(BaseModel):
    id: str
    client_id: str
    origin: str
    destination: str
    trip_type: str
    departure_date_from: date
    departure_date_to: date
    return_date_from: Optional[date]
    return_date_to: Optional[date]
    adults: int
    max_stops: Optional[int]
    threshold_price: Decimal
    alert_email: str
    created_at: datetime
    is_active: bool
    current_best_price: Optional[Decimal]
    last_checked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PriceSnapshotResponse(BaseModel):
    checked_at: datetime
    best_price: Decimal
    currency: str

    model_config = {"from_attributes": True}


class PriceHistoryResponse(BaseModel):
    tracked_search_id: str
    snapshots: list[PriceSnapshotResponse]
