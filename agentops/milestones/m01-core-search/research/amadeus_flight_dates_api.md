# Research: Amadeus Flight Cheapest Date Search API

Source: https://github.com/amadeus4dev/amadeus-python (SDK source)
Source: https://github.com/amadeus4dev/amadeus-code-examples (examples)
Source: https://raw.githubusercontent.com/amadeus4dev/amadeus-python/master/README.rst

## Endpoint

`GET /v1/shopping/flight-dates`

SDK accessor: `amadeus.shopping.flight_dates.get(**params)`

## Parameters

The SDK `get()` method accepts `**params` and passes them directly to the endpoint.
Documented parameters (from SDK docstring):

- `origin` (required): IATA code of departure city/airport (e.g. `"NYC"`)
- `destination` (required): IATA code of arrival city/airport (e.g. `"MAD"`)

The docstring does NOT document a `departureDate` parameter, and the README example calls
`amadeus.shopping.flight_dates.get(origin='NYC', destination='MAD')` with no date
parameter. This indicates the API returns a spread of the cheapest prices across
multiple departure dates **in a single call** without requiring a specific date range.

The underlying REST API does accept optional date filtering params
(`departureDate`, `oneWay`, `duration`, `nonStop`, `maxPrice`, `currency`, `viewBy`)
but the SDK passes any `**params` through, so callers can supply them.

## Key Behavioral Finding

The Flight Cheapest Date Search API returns a **calendar of prices** — multiple
departure dates with their associated cheapest fares — in a **single API call**.
It does NOT require one call per date. This is designed specifically for "find the
cheapest day to fly in a window" use cases.

The `viewBy=DATE` parameter groups results by departure date.

## Response Structure (from API spec)

Each item in `response.data` contains:
```json
{
  "type": "flight-date",
  "origin": "MAD",
  "destination": "BOS",
  "departureDate": "2024-11-01",
  "returnDate": "2024-11-08",
  "price": {
    "total": "98.53"
  },
  "links": {
    "flightDates": "...",
    "flightOffers": "..."
  }
}
```

The `links.flightOffers` URL provides the direct link to search flight offers
for that specific date — enabling efficient two-step search (cheapest dates first,
then offers for top-N dates).

## Flight Offers Search

`GET /v2/shopping/flight-offers`

SDK accessor: `amadeus.shopping.flight_offers_search.get(**params)`

Key parameters:
- `originLocationCode` (required): IATA origin
- `destinationLocationCode` (required): IATA destination
- `departureDate` (required): `YYYY-MM-DD` — a single date per call
- `adults` (required): number of adult passengers
- `nonStop` (optional): `true`/`false`
- `max` (optional): max number of results (default 250)
- `currencyCode` (optional)

**Important**: Flight Offers Search accepts one date at a time. For a date range,
the design must call it once per selected date or leverage the `flightOffers` link
from flight-dates response.

## Airport & City Search

`GET /v1/reference-data/locations`

SDK accessor: `amadeus.reference_data.locations.get(keyword=..., subType=...)`

Parameters:
- `keyword` (required): search string (start of city/airport name or IATA code)
- `subType` (required): `"AIRPORT"`, `"CITY"`, or `"AIRPORT,CITY"` (use `Location.ANY`)
- `page[limit]` (optional): max results (use 10 for autocomplete)

Response: array of location objects with `iataCode`, `name`, `address.cityName`.
