"""Tests for flight_service.py — TDD for t05."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.schemas.search import AirportResult, FlightOfferResponse, SearchRequest, SegmentInfo
from app.services.flight_service import (
    _build_cache_key,
    _cache,
    _cache_lock,
    search_airports,
    search_flights,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    *,
    origin: str = "JFK",
    destination: str = "LAX",
    trip_type: str = "one_way",
    departure_date_from: date = date(2026, 6, 1),
    departure_date_to: date = date(2026, 6, 10),
    return_date_from: date | None = None,
    return_date_to: date | None = None,
    adults: int = 1,
    max_stops: int | None = None,
) -> SearchRequest:
    return SearchRequest(
        origin=origin,
        destination=destination,
        trip_type=trip_type,
        departure_date_from=departure_date_from,
        departure_date_to=departure_date_to,
        return_date_from=return_date_from,
        return_date_to=return_date_to,
        adults=adults,
        max_stops=max_stops,
    )


def _make_segment_dict(
    carrier: str = "AA",
    number: str = "100",
    dep_iata: str = "JFK",
    dep_at: str = "2026-06-01T08:00:00",
    arr_iata: str = "LAX",
    arr_at: str = "2026-06-01T11:00:00",
    duration: str = "PT5H",
    stops: int = 0,
) -> dict:
    return {
        "carrierCode": carrier,
        "number": number,
        "departure": {"iataCode": dep_iata, "at": dep_at},
        "arrival": {"iataCode": arr_iata, "at": arr_at},
        "duration": duration,
        "numberOfStops": stops,
    }


def _make_offer(
    price: str = "100.00",
    currency: str = "USD",
    segments: list[dict] | None = None,
    return_segments: list[dict] | None = None,
) -> dict:
    if segments is None:
        segments = [_make_segment_dict()]
    itineraries = [{"segments": segments}]
    if return_segments is not None:
        itineraries.append({"segments": return_segments})
    return {
        "price": {"grandTotal": price, "currency": currency},
        "itineraries": itineraries,
    }


def _make_mock_client(
    dates_data: list[dict] | None = None,
    offers_data: list[dict] | None = None,
) -> MagicMock:
    client = MagicMock()
    dates_resp = MagicMock()
    dates_resp.data = dates_data if dates_data is not None else []
    client.shopping.flight_dates.get.return_value = dates_resp

    offers_resp = MagicMock()
    offers_resp.data = offers_data if offers_data is not None else []
    client.shopping.flight_offers_search.get.return_value = offers_resp

    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the module-level TTLCache before and after each test."""
    with _cache_lock:
        _cache.clear()
    yield
    with _cache_lock:
        _cache.clear()


# ---------------------------------------------------------------------------
# search_airports tests (kept from prior tasks)
# ---------------------------------------------------------------------------

class TestSearchAirports:
    def test_returns_list_of_airport_results(self):
        client = MagicMock()
        response = MagicMock()
        response.data = [
            {
                "iataCode": "JFK",
                "name": "John F Kennedy Intl",
                "address": {"cityName": "New York", "countryName": "United States"},
            }
        ]
        client.reference_data.locations.get.return_value = response

        results = search_airports("JFK", client)

        assert len(results) == 1
        assert isinstance(results[0], AirportResult)
        assert results[0].iata_code == "JFK"
        assert results[0].name == "John F Kennedy Intl"
        assert results[0].city == "New York"
        assert results[0].country == "United States"

    def test_missing_address_fields_default_to_empty_string(self):
        client = MagicMock()
        response = MagicMock()
        response.data = [{"iataCode": "ABC", "name": "Test Airport"}]
        client.reference_data.locations.get.return_value = response

        results = search_airports("ABC", client)

        assert results[0].city == ""
        assert results[0].country == ""

    def test_passes_correct_params_to_amadeus(self):
        from amadeus import Location

        client = MagicMock()
        response = MagicMock()
        response.data = []
        client.reference_data.locations.get.return_value = response

        search_airports("NYC", client)

        client.reference_data.locations.get.assert_called_once_with(
            keyword="NYC",
            subType=Location.ANY,
            **{"page[limit]": 10},
        )


# ---------------------------------------------------------------------------
# search_flights tests
# ---------------------------------------------------------------------------

class TestSearchFlightsCacheHit:
    def test_cache_hit_skips_amadeus_call(self):
        """Pre-populate cache; search_flights must return cached result without calling Amadeus."""
        request = _make_request()
        cached_result = [
            FlightOfferResponse(
                price="99.00",
                currency="USD",
                departure_date=date(2026, 6, 1),
                outbound_segments=[
                    SegmentInfo(
                        airline="AA",
                        flight_number="AA 100",
                        departure_airport="JFK",
                        departure_time="2026-06-01T08:00:00",
                        arrival_airport="LAX",
                        arrival_time="2026-06-01T11:00:00",
                        duration="PT5H",
                        stops=0,
                    )
                ],
            )
        ]
        key = _build_cache_key(request)
        with _cache_lock:
            _cache[key] = cached_result

        client = MagicMock()
        result = search_flights(request, client)

        assert result is cached_result
        client.shopping.flight_dates.get.assert_not_called()
        client.shopping.flight_offers_search.get.assert_not_called()


class TestSearchFlightsCacheMiss:
    def test_cache_miss_calls_amadeus_and_caches_result(self):
        """On a cache miss, amadeus is called; result is stored in cache."""
        request = _make_request(
            departure_date_from=date(2026, 6, 1),
            departure_date_to=date(2026, 6, 10),
        )
        dates_data = [{"departureDate": "2026-06-03", "price": {"total": "150.00"}}]
        offers_data = [_make_offer("150.00")]
        client = _make_mock_client(dates_data=dates_data, offers_data=offers_data)

        result = search_flights(request, client)

        client.shopping.flight_dates.get.assert_called_once()
        assert len(result) == 1
        assert isinstance(result[0], FlightOfferResponse)

        key = _build_cache_key(request)
        with _cache_lock:
            assert key in _cache
            assert _cache[key] == result

    def test_one_way_uses_oneWay_param(self):
        """One-way trip passes oneWay='true' to flight_dates.get."""
        request = _make_request(trip_type="one_way")
        client = _make_mock_client(dates_data=[], offers_data=[])

        search_flights(request, client)

        call_kwargs = client.shopping.flight_dates.get.call_args.kwargs
        assert call_kwargs.get("oneWay") == "true"

    def test_round_trip_omits_oneWay_param(self):
        """Round-trip does NOT pass oneWay param to flight_dates.get."""
        request = _make_request(
            trip_type="round_trip",
            departure_date_from=date(2026, 6, 1),
            departure_date_to=date(2026, 6, 10),
            return_date_from=date(2026, 6, 15),
            return_date_to=date(2026, 6, 25),
        )
        client = _make_mock_client(dates_data=[], offers_data=[])

        search_flights(request, client)

        call_kwargs = client.shopping.flight_dates.get.call_args.kwargs
        assert "oneWay" not in call_kwargs


class TestDateFiltering:
    def test_only_in_window_dates_passed_to_offers_search(self):
        """Only dates within the departure window are used in flight_offers_search calls."""
        request = _make_request(
            departure_date_from=date(2026, 6, 5),
            departure_date_to=date(2026, 6, 7),
        )
        dates_data = [
            {"departureDate": "2026-06-01", "price": {"total": "100.00"}},  # outside
            {"departureDate": "2026-06-05", "price": {"total": "120.00"}},  # inside
            {"departureDate": "2026-06-06", "price": {"total": "110.00"}},  # inside
            {"departureDate": "2026-06-10", "price": {"total": "90.00"}},   # outside
        ]
        offers_data = [_make_offer("110.00")]
        client = _make_mock_client(dates_data=dates_data, offers_data=offers_data)

        search_flights(request, client)

        # Only 2 dates are in window → offers_search called exactly twice
        assert client.shopping.flight_offers_search.get.call_count == 2
        called_dates = {
            call.kwargs["departureDate"]
            for call in client.shopping.flight_offers_search.get.call_args_list
        }
        assert called_dates == {"2026-06-05", "2026-06-06"}

    def test_empty_when_no_dates_in_window(self):
        """Returns empty list when no calendar dates fall within departure window."""
        request = _make_request(
            departure_date_from=date(2026, 7, 1),
            departure_date_to=date(2026, 7, 10),
        )
        dates_data = [
            {"departureDate": "2026-06-01", "price": {"total": "100.00"}},
            {"departureDate": "2026-06-15", "price": {"total": "110.00"}},
        ]
        client = _make_mock_client(dates_data=dates_data, offers_data=[])

        result = search_flights(request, client)

        assert result == []
        client.shopping.flight_offers_search.get.assert_not_called()

    def test_top_5_dates_by_price_taken(self):
        """Only the 5 cheapest dates by calendar price are queried for offers."""
        request = _make_request(
            departure_date_from=date(2026, 6, 1),
            departure_date_to=date(2026, 6, 30),
        )
        # 8 dates in window, top 5 cheapest prices are 100–140
        dates_data = [
            {"departureDate": f"2026-06-{str(i).zfill(2)}", "price": {"total": str(100 + i * 10 - 10)}}  # noqa: E501
            for i in range(1, 9)
        ]
        client = _make_mock_client(dates_data=dates_data, offers_data=[_make_offer("100.00")])

        search_flights(request, client)

        assert client.shopping.flight_offers_search.get.call_count == 5


class TestMaxStopsFiltering:
    def test_max_stops_0_passes_nonStop_param(self):
        """max_stops=0 sets nonStop='true' in flight_offers_search call."""
        request = _make_request(max_stops=0)
        dates_data = [{"departureDate": "2026-06-03", "price": {"total": "100.00"}}]
        client = _make_mock_client(dates_data=dates_data, offers_data=[_make_offer("100.00")])

        search_flights(request, client)

        call_kwargs = client.shopping.flight_offers_search.get.call_args.kwargs
        assert call_kwargs.get("nonStop") == "true"

    def test_max_stops_1_filters_multi_stop_offers(self):
        """max_stops=1 keeps nonstop (0 stops) and 1-stop; excludes 2+ stops."""
        request = _make_request(max_stops=1)
        dates_data = [{"departureDate": "2026-06-03", "price": {"total": "100.00"}}]

        # Nonstop: 1 segment → 0 stops
        nonstop_offer = _make_offer("80.00", segments=[_make_segment_dict()])
        # 1-stop: 2 segments → 1 stop
        one_stop_offer = _make_offer(
            "90.00",
            segments=[_make_segment_dict(), _make_segment_dict(dep_iata="ORD", arr_iata="LAX")],
        )
        # 2-stop: 3 segments → 2 stops
        two_stop_offer = _make_offer(
            "70.00",
            segments=[
                _make_segment_dict(),
                _make_segment_dict(dep_iata="ORD", arr_iata="DFW"),
                _make_segment_dict(dep_iata="DFW", arr_iata="LAX"),
            ],
        )
        client = _make_mock_client(
            dates_data=dates_data,
            offers_data=[nonstop_offer, one_stop_offer, two_stop_offer],
        )

        result = search_flights(request, client)

        assert len(result) == 2
        prices = {r.price for r in result}
        assert prices == {"80.00", "90.00"}

    def test_max_stops_none_does_not_filter(self):
        """max_stops=None keeps all offers regardless of stop count."""
        request = _make_request(max_stops=None)
        dates_data = [{"departureDate": "2026-06-03", "price": {"total": "100.00"}}]
        offers_data = [
            _make_offer("80.00", segments=[_make_segment_dict()]),
            _make_offer(
                "70.00",
                segments=[
                    _make_segment_dict(),
                    _make_segment_dict(dep_iata="ORD", arr_iata="DFW"),
                    _make_segment_dict(dep_iata="DFW", arr_iata="LAX"),
                ],
            ),
        ]
        client = _make_mock_client(dates_data=dates_data, offers_data=offers_data)

        result = search_flights(request, client)

        assert len(result) == 2


class TestResultSorting:
    def test_results_sorted_by_price_ascending(self):
        """Results are sorted by grandTotal price ascending."""
        request = _make_request()
        dates_data = [{"departureDate": "2026-06-03", "price": {"total": "100.00"}}]
        offers_data = [
            _make_offer("150.00"),
            _make_offer("89.99"),
            _make_offer("200.00"),
        ]
        client = _make_mock_client(dates_data=dates_data, offers_data=offers_data)

        result = search_flights(request, client)

        assert len(result) == 3
        assert result[0].price == "89.99"
        assert result[1].price == "150.00"
        assert result[2].price == "200.00"


class TestRoundTripMapping:
    def test_round_trip_offer_mapped_with_return_itinerary(self):
        """Round-trip offer has outbound_segments, return_segments, return_date populated."""
        request = _make_request(
            trip_type="round_trip",
            departure_date_from=date(2026, 6, 1),
            departure_date_to=date(2026, 6, 10),
            return_date_from=date(2026, 6, 15),
            return_date_to=date(2026, 6, 25),
        )
        dates_data = [
            {
                "departureDate": "2026-06-05",
                "returnDate": "2026-06-20",
                "price": {"total": "300.00"},
            }
        ]
        outbound_seg = _make_segment_dict(
            dep_iata="JFK", arr_iata="LAX",
            dep_at="2026-06-05T08:00:00", arr_at="2026-06-05T11:00:00"
        )
        return_seg = _make_segment_dict(
            dep_iata="LAX", arr_iata="JFK",
            dep_at="2026-06-20T12:00:00", arr_at="2026-06-20T20:00:00"
        )
        offer = _make_offer(
            price="300.00",
            segments=[outbound_seg],
            return_segments=[return_seg],
        )

        client = _make_mock_client(dates_data=dates_data, offers_data=[offer])

        result = search_flights(request, client)

        assert len(result) == 1
        r = result[0]
        assert r.departure_date == date(2026, 6, 5)
        assert r.return_date == date(2026, 6, 20)
        assert len(r.outbound_segments) == 1
        assert len(r.return_segments) == 1
        assert r.outbound_segments[0].departure_airport == "JFK"
        assert r.outbound_segments[0].arrival_airport == "LAX"
        assert r.return_segments[0].departure_airport == "LAX"
        assert r.return_segments[0].arrival_airport == "JFK"

    def test_round_trip_passes_returnDate_to_offers_search(self):
        """Round-trip calls flight_offers_search with returnDate param."""
        request = _make_request(
            trip_type="round_trip",
            departure_date_from=date(2026, 6, 1),
            departure_date_to=date(2026, 6, 10),
            return_date_from=date(2026, 6, 15),
            return_date_to=date(2026, 6, 25),
        )
        dates_data = [
            {
                "departureDate": "2026-06-05",
                "returnDate": "2026-06-20",
                "price": {"total": "300.00"},
            }
        ]
        client = _make_mock_client(dates_data=dates_data, offers_data=[])

        search_flights(request, client)

        call_kwargs = client.shopping.flight_offers_search.get.call_args.kwargs
        assert call_kwargs.get("returnDate") == "2026-06-20"


class TestSegmentMapping:
    def test_segment_fields_mapped_correctly(self):
        """Individual segment fields map to SegmentInfo correctly."""
        request = _make_request()
        dates_data = [{"departureDate": "2026-06-03", "price": {"total": "100.00"}}]
        seg = _make_segment_dict(
            carrier="UA",
            number="456",
            dep_iata="SFO",
            dep_at="2026-06-03T07:30:00",
            arr_iata="ORD",
            arr_at="2026-06-03T13:45:00",
            duration="PT4H15M",
            stops=0,
        )
        client = _make_mock_client(dates_data=dates_data, offers_data=[_make_offer(segments=[seg])])

        result = search_flights(request, client)

        assert len(result) == 1
        s = result[0].outbound_segments[0]
        assert s.airline == "UA"
        assert s.flight_number == "UA 456"
        assert s.departure_airport == "SFO"
        assert s.departure_time == "2026-06-03T07:30:00"
        assert s.arrival_airport == "ORD"
        assert s.arrival_time == "2026-06-03T13:45:00"
        assert s.duration == "PT4H15M"
        assert s.stops == 0
