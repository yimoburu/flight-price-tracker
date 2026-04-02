from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.tracked_search import PriceSnapshot, TrackedSearch
from app.schemas.tracking import (
    CreateTrackedSearchRequest,
    PriceHistoryResponse,
    PriceSnapshotResponse,
    TrackedSearchResponse,
)

router = APIRouter(prefix="/api/v1", tags=["tracking"])


def get_client_id(x_client_id: str = Header(..., alias="X-Client-ID")) -> str:
    try:
        uuid.UUID(x_client_id, version=4)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="X-Client-ID must be a valid UUID v4")
    return x_client_id


def _enrich(search: TrackedSearch, db: Session) -> TrackedSearch:
    """Populate current_best_price and last_checked_at from the latest snapshot."""
    latest = (
        db.query(PriceSnapshot)
        .filter(PriceSnapshot.tracked_search_id == search.id)
        .order_by(PriceSnapshot.checked_at.desc())
        .first()
    )
    search.current_best_price = latest.best_price if latest else None
    search.last_checked_at = latest.checked_at if latest else None
    return search


@router.post("/tracked-searches", response_model=TrackedSearchResponse, status_code=201)
def create_tracked_search(
    body: CreateTrackedSearchRequest,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> TrackedSearchResponse:
    ts = TrackedSearch(
        client_id=client_id,
        origin=body.origin,
        destination=body.destination,
        trip_type=body.trip_type,
        departure_date_from=body.departure_date_from,
        departure_date_to=body.departure_date_to,
        return_date_from=body.return_date_from,
        return_date_to=body.return_date_to,
        adults=body.adults,
        max_stops=body.max_stops,
        threshold_price=body.threshold_price,
        alert_email=str(body.alert_email),
    )
    db.add(ts)
    db.commit()
    db.refresh(ts)
    ts.current_best_price = None
    ts.last_checked_at = None
    return TrackedSearchResponse.model_validate(ts)


@router.get("/tracked-searches", response_model=list[TrackedSearchResponse])
def list_tracked_searches(
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> list[TrackedSearchResponse]:
    searches = (
        db.query(TrackedSearch)
        .filter(TrackedSearch.client_id == client_id, TrackedSearch.is_active == True)  # noqa: E712
        .all()
    )
    return [TrackedSearchResponse.model_validate(_enrich(s, db)) for s in searches]


@router.delete("/tracked-searches/{search_id}", status_code=204)
def delete_tracked_search(
    search_id: str,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> None:
    ts = (
        db.query(TrackedSearch)
        .filter(TrackedSearch.id == search_id, TrackedSearch.client_id == client_id)
        .first()
    )
    if ts is None:
        raise HTTPException(status_code=404, detail="Tracked search not found")
    ts.is_active = False
    db.commit()
    return None


@router.get("/tracked-searches/{search_id}/history", response_model=PriceHistoryResponse)
def get_price_history(
    search_id: str,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> PriceHistoryResponse:
    ts = (
        db.query(TrackedSearch)
        .filter(TrackedSearch.id == search_id, TrackedSearch.client_id == client_id)
        .first()
    )
    if ts is None:
        raise HTTPException(status_code=404, detail="Tracked search not found")
    snapshots = (
        db.query(PriceSnapshot)
        .filter(PriceSnapshot.tracked_search_id == search_id)
        .order_by(PriceSnapshot.checked_at.asc())
        .all()
    )
    return PriceHistoryResponse(
        tracked_search_id=search_id,
        snapshots=[PriceSnapshotResponse.model_validate(s) for s in snapshots],
    )
