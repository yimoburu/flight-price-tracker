# Research: Amadeus Python SDK

Source: https://github.com/amadeus4dev/amadeus-python
Source: https://pypi.org/project/amadeus/
Source: https://raw.githubusercontent.com/amadeus4dev/amadeus-python/master/README.rst

## SDK Overview

- Package: `amadeus` (pip install amadeus)
- Python: requires 3.8+
- Dependencies: **none** — uses only Python stdlib (`urllib.request`, `urllib.parse`, `urllib.error`)
- License: MIT
- Maintained by Amadeus

## HTTP Client Implementation

The SDK is **100% synchronous and blocking**. The call chain is:

```
amadeus.shopping.flight_dates.get()
  → HTTP.get()
  → HTTP.request()
  → HTTP._unauthenticated_request()
  → HTTP.__execute()
  → HTTP.__fetch()
    → self.http(request.http_request)   # <-- blocking urllib.request.urlopen call
```

The `self.http` callable defaults to `urllib.request.urlopen` (documented in the
`Client.__init__` docstring: "a urllib.request.urlopen compatible client ...
Default: urlopen"). It can be overridden via the `http=` constructor parameter for
testing.

## Authentication

SDK handles OAuth2 automatically:
- Reads `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` from environment if not
  passed to constructor
- Caches the access token and refreshes it when expired
- `hostname` parameter: `"test"` (default sandbox) or `"production"`

```python
from amadeus import Client, ResponseError

amadeus = Client(
    client_id='...',
    client_secret='...',
    hostname='test'  # or 'production'
)
```

Or with environment variables:
```python
amadeus = Client()  # reads AMADEUS_CLIENT_ID, AMADEUS_CLIENT_SECRET from env
```

## Error Handling

- All API errors raise `amadeus.ResponseError`
- Subclasses: `AuthenticationError`, `NotFoundError`, `RateLimitError`, `ServerError`, etc.
- Access via `error.response.result` for response body and `error.response.status_code`

## Key API Methods Used in This Project

```python
# Flight cheapest dates (returns calendar of prices in one call)
response = amadeus.shopping.flight_dates.get(
    origin='NYC',
    destination='MAD'
    # optional: departureDate='2024-11-01', nonStop='true', viewBy='DATE'
)
# response.data -> list of {departureDate, returnDate, price.total, links.flightOffers}

# Flight offers (single date)
response = amadeus.shopping.flight_offers_search.get(
    originLocationCode='MAD',
    destinationLocationCode='BOS',
    departureDate='2024-11-01',
    adults=1,
    nonStop='false',
    max=5
)
# response.data -> list of flight offer objects with itineraries, price, etc.

# Airport/city autocomplete
from amadeus import Location
response = amadeus.reference_data.locations.get(
    keyword='LON',
    subType=Location.ANY,
    **{'page[limit]': 10}
)
# response.data -> list of {iataCode, name, address.cityName, address.countryName}
```
