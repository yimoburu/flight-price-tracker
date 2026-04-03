# POC: Amadeus Date Range API Behavior

## Question

Does the `Flight Cheapest Date Search` endpoint (`/v1/shopping/flight-dates`) return
the cheapest prices for multiple departure dates in a single API call, or does it
require one call per departure date?

## Success Criteria

- **VIABLE**: Single call to `flight_dates.get(origin=X, destination=Y)` returns a
  list of objects each containing a `departureDate` and `price.total` — covering
  multiple dates.
- **NOT_VIABLE**: The API only returns a single date's price and requires iteration,
  making N calls for N dates.

## Approach

No running sandbox credentials were available to make live API calls. The investigation
was conducted via:

1. Reading the Amadeus Python SDK source on GitHub (`amadeus-python` repository), in
   particular `amadeus/shopping/_flight_dates.py` and its docstring.
2. Reading the official README.rst examples for the SDK.
3. Reading the `amadeus-code-examples` repository structure which confirms a standalone
   `flight_cheapest_date_search/v1/get` example exists (i.e., it is a single-request
   pattern, not a loop).
4. Examining the SDK `**params` pass-through design, which confirms additional optional
   parameters (`departureDate`, `viewBy`, `nonStop`, `duration`, `maxPrice`) can be
   passed but are not required — meaning the default call returns a spread of dates.
5. Cross-referencing with the Amadeus API reference naming convention: "Cheapest Date
   Search" (plural concept: "dates") vs. "Flight Offers Search" (which takes a single
   `departureDate`).

## Results

Evidence gathered from SDK source and documentation:

1. **SDK method signature**: `flight_dates.get(origin='NYC', destination='MAD')` — the
   README example passes only `origin` and `destination`, with no `departureDate`.
   If the API returned only one date, a date parameter would be required.

2. **Response shape**: The API response contains an array (`response.data`) where each
   element has `departureDate`, `returnDate`, and `price.total` fields. This is a
   calendar/list structure — multiple rows, one per date.

3. **`links.flightOffers` per item**: Each date result includes a pre-built URL to
   search actual flight offers for that specific date, confirming the intended two-step
   workflow: get cheapest dates calendar → follow links for the top dates' offers.

4. **Optional `viewBy` parameter**: Documented `viewBy=DATE` groups results by
   departure date. The existence of this parameter confirms multi-date results.

5. **Code example repository**: A standalone `flight_cheapest_date_search/v1/get`
   example directory exists (not a loop example), consistent with a single-call pattern.

6. **Amadeus product positioning**: The endpoint is explicitly marketed as
   "Find the cheapest date to fly" — a range-discovery tool, not a single-date lookup.

## Conclusion

**Verdict:** VIABLE

The `Flight Cheapest Date Search` endpoint returns a **calendar of cheapest prices
across multiple departure dates in a single API call**. No date range parameters are
required — the API returns its own date spread (typically 1–3 months out from today).
Optional parameters `departureDate` (specific date), `nonStop`, `duration`, and
`viewBy` can narrow or reshape results, but the default call returns multiple dates.

**Design implication**: The search service should:
1. Call `flight_dates.get(origin, destination)` once to get cheapest dates.
2. Filter the returned dates to those within the user's requested `departure_date_from`
   to `departure_date_to` window.
3. Call `flight_offers_search.get(...)` for the top-N cheapest filtered dates (e.g., top 5)
   to get actual detailed flight offers.

This avoids calling `flight_offers_search` for every date in the range (which would
be 1–30 API calls) and instead uses at most 5–10 calls for the most relevant dates.

## Limitations

- No live API call was made; response field names are inferred from SDK source and
  documentation structure (not a captured live response).
- The exact set of dates returned by default (how far out, how many results) was not
  measured — it may vary by route.
- Round-trip behavior (returnDate in results) was not confirmed via live call; the
  PRD's design calls for filtering return dates in the user layer.
- The optional `departureDate` parameter format (single date vs. comma-separated range)
  was not confirmed — safer to rely on client-side filtering of the calendar response.
