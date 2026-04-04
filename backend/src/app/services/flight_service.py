import threading
from datetime import date, timedelta

from amadeus import Client, Location, ResponseError
from cachetools import TTLCache

from app.schemas.search import AirportResult, FlightOfferResponse, SearchRequest, SegmentInfo

# Module-level cache: max 128 entries, 15-minute TTL
_cache: TTLCache = TTLCache(maxsize=128, ttl=900)
_cache_lock: threading.Lock = threading.Lock()


def search_airports(query: str, client: Client) -> list[AirportResult]:
    """Search airports and cities by keyword."""
    response = client.reference_data.locations.get(
        keyword=query,
        subType=Location.ANY,
        **{"page[limit]": 10},
    )
    return [
        AirportResult(
            iata_code=item["iataCode"],
            name=item["name"],
            city=item.get("address", {}).get("cityName", ""),
            country=item.get("address", {}).get("countryName", ""),
        )
        for item in response.data
    ]


def _build_cache_key(request: SearchRequest) -> tuple:
    """Build a hashable cache key from all search parameters."""
    return (
        request.origin,
        request.destination,
        request.trip_type,
        str(request.departure_date_from),
        str(request.departure_date_to),
        str(request.return_date_from),
        str(request.return_date_to),
        request.adults,
        request.max_stops,
    )


def _map_segment(seg: dict) -> SegmentInfo:
    return SegmentInfo(
        airline=seg["carrierCode"],
        flight_number=f"{seg['carrierCode']} {seg['number']}",
        departure_airport=seg["departure"]["iataCode"],
        departure_time=seg["departure"]["at"],
        arrival_airport=seg["arrival"]["iataCode"],
        arrival_time=seg["arrival"]["at"],
        duration=seg["duration"],
        stops=seg.get("numberOfStops", 0),
    )


def _map_offer_to_response(offer: dict, trip_type: str) -> FlightOfferResponse:
    """Map a raw Amadeus flight offer dict to FlightOfferResponse."""
    price = offer["price"]["grandTotal"]
    currency = offer["price"]["currency"]
    outbound = offer["itineraries"][0]
    outbound_segments = [_map_segment(s) for s in outbound["segments"]]
    departure_date = date.fromisoformat(outbound["segments"][0]["departure"]["at"][:10])
    return_date = None
    return_segments: list[SegmentInfo] = []
    if trip_type == "round_trip" and len(offer["itineraries"]) > 1:
        return_itin = offer["itineraries"][1]
        return_segments = [_map_segment(s) for s in return_itin["segments"]]
        return_date = date.fromisoformat(return_itin["segments"][0]["departure"]["at"][:10])
    return FlightOfferResponse(
        price=price,
        currency=currency,
        departure_date=departure_date,
        return_date=return_date,
        outbound_segments=outbound_segments,
        return_segments=return_segments,
    )


def search_flights(request: SearchRequest, client: Client) -> list[FlightOfferResponse]:
    """Search for flight offers across a date range with TTL caching."""
    cache_key = _build_cache_key(request)
    with _cache_lock:
        if cache_key in _cache:
            return _cache[cache_key]  # type: ignore[return-value]

    # Step 1 & 2: Get cheapest date calendar or fallback
    filtered = []
    try:
        if request.trip_type == "one_way":
            dates_response = client.shopping.flight_dates.get(
                origin=request.origin,
                destination=request.destination,
                oneWay="true",
            )
        else:
            dates_response = client.shopping.flight_dates.get(
                origin=request.origin,
                destination=request.destination,
            )

        for item in dates_response.data:
            dep_date = date.fromisoformat(item["departureDate"])
            if not (request.departure_date_from <= dep_date <= request.departure_date_to):
                continue
            if request.trip_type == "round_trip":
                ret_date = date.fromisoformat(item.get("returnDate", "9999-01-01"))
                if request.return_date_from and request.return_date_to:
                    if not (request.return_date_from <= ret_date <= request.return_date_to):
                        continue
            filtered.append(item)
    except ResponseError as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code in (404, 400):
            d = request.departure_date_from
            while d <= request.departure_date_to and len(filtered) < 5:
                item = {"departureDate": str(d)}
                if request.trip_type == "round_trip" and request.return_date_from:
                    item["returnDate"] = str(request.return_date_from)
                filtered.append(item)
                d += timedelta(days=1)
        else:
            raise

    if not filtered:
        with _cache_lock:
            _cache[cache_key] = []
        return []

    # Step 3: Sort by price, take top 5
    filtered.sort(key=lambda x: float(x.get("price", {}).get("total", "9999")))
    top_dates = filtered[:5]

    # Step 4: Fetch flight offers for each top date
    all_offers: list[dict] = []
    for date_item in top_dates:
        params: dict = {
            "originLocationCode": request.origin,
            "destinationLocationCode": request.destination,
            "departureDate": str(date_item["departureDate"]),
            "adults": request.adults,
            "max": 10,
        }
        if request.trip_type == "round_trip":
            params["returnDate"] = str(date_item["returnDate"])
        if request.max_stops == 0:
            params["nonStop"] = "true"
        offers_response = client.shopping.flight_offers_search.get(**params)
        all_offers.extend(offers_response.data)

    # Step 5: Filter by max_stops (if max_stops is 1 or 2)
    if request.max_stops is not None and request.max_stops > 0:

        def count_stops(offer: dict) -> int:
            return len(offer["itineraries"][0]["segments"]) - 1

        all_offers = [o for o in all_offers if count_stops(o) <= request.max_stops]

    # Step 6: Sort by price, map to response
    all_offers.sort(key=lambda o: float(o["price"]["grandTotal"]))
    results = [_map_offer_to_response(o, request.trip_type) for o in all_offers]

    with _cache_lock:
        _cache[cache_key] = results
    return results
