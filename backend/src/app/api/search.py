from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.schemas.search import AirportResult, FlightOfferResponse, SearchRequest
from app.services.amadeus_client import get_amadeus_client
from app.services.flight_service import search_airports, search_flights

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/airports", response_model=list[AirportResult])
async def airports(
    q: str = Query(..., min_length=3, description="Airport/city search keyword"),
    settings: Settings = Depends(get_settings),
) -> list[AirportResult]:
    client = get_amadeus_client()
    return search_airports(q, client)


@router.post("/search", response_model=list[FlightOfferResponse])
def search(body: SearchRequest) -> list[FlightOfferResponse]:
    client = get_amadeus_client()
    return search_flights(body, client)
