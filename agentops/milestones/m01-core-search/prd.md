# PRD: m01 — Core Search

## Overview

This milestone delivers the foundational flight search web app: a FastAPI backend integrating the Amadeus API for real-time flight price data, and a React/TypeScript frontend where users can search one-way or round-trip flights across a range of dates and view a price grid of results. This is the core user-facing value: type in a route and date window, see the cheapest fares.

## User Stories

- As a traveler, I want to search for one-way flights between two airports across a range of departure dates so I can find the cheapest day to fly.
- As a traveler, I want to search for round-trip flights with flexible outbound and return date ranges so I can see which combination of dates gives the lowest total fare.
- As a traveler, I want to see results displayed as a price grid (date vs. price) so I can compare fares at a glance.
- As a traveler, I want to filter results by number of stops (nonstop, 1 stop, any) so I can narrow down options.
- As a traveler, I want to see per-result details (airline, departure/arrival time, duration, number of stops, price) so I can make an informed choice.

## Functional Requirements

### Backend (FastAPI)

1. **Flight search endpoint** `POST /api/v1/search`
  - Accepts: `origin` (IATA code), `destination` (IATA code), `trip_type` (`one_way` | `round_trip`), `departure_date_from` (YYYY-MM-DD), `departure_date_to` (YYYY-MM-DD), `return_date_from` (YYYY-MM-DD, round-trip only), `return_date_to` (YYYY-MM-DD, round-trip only), `adults` (int, default 1), `max_stops` (int | null, default null = any)
  - Returns: list of flight offers sorted by price ascending, each with `price`, `currency`, `departure_date`, `return_date` (if round-trip), `segments` (airline, flight number, departure time, arrival time, duration, stops)
  - For date ranges: calls Amadeus `Flight Cheapest Date Search` (`/shopping/flight-dates`) first to find cheapest dates in range, then calls `Flight Offers Search` for the top results
  - Accepts criteria: departure date range spans max 30 days; return date range spans max 30 days
  - Validation: IATA codes must be 3 uppercase letters; dates must be valid ISO 8601 and not in the past
2. **Airport search endpoint** `GET /api/v1/airports?q={query}`
  - Returns matching airports (IATA code + city + airport name) for autocomplete
  - Uses Amadeus Airport & City Search API
  - Returns max 10 results
3. **Health check** `GET /api/v1/health`
  - Returns `{"status": "ok"}`
4. **Configuration** (via `.env`):
  - `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET` (required)
  - `AMADEUS_HOSTNAME` (default: `test` for sandbox)
  - `CORS_ORIGINS` (default: `http://localhost:5173`)
5. **Error handling**:
  - Amadeus API errors → mapped to appropriate HTTP status codes with `{"detail": "..."}` body
  - Rate limit errors → 429 with retry guidance
  - Invalid IATA codes → 422 validation error
  - No results found → 200 with empty list (not an error)
6. **Caching**: In-memory cache (TTL 15 minutes) for identical search requests to avoid exhausting free-tier quota

### Frontend (React + TypeScript)

1. **Search form**:
  - Origin airport autocomplete input (calls `/api/v1/airports` on keystroke, debounced 300ms)
  - Destination airport autocomplete input (same)
  - Trip type toggle: One Way / Round Trip
  - Departure date range picker: `Departure from` and `Departure to` (calendar date pickers, max 30-day range enforced in UI)
  - Return date range picker (visible only for round-trip): `Return from` and `Return to`
  - Adults count selector (1–9)
  - Max stops filter: Any / Nonstop / 1 stop
  - Search button (disabled while search in progress)
2. **Results display**:
  - Loading state while API call in progress
  - Error state with human-readable message if search fails
  - Empty state when no results found
  - Results list sorted by price, each card showing:
    - Total price (with currency)
    - Departure date (and return date for round trips)
    - Outbound segments: airline logo/code, flight number, departure airport + time, arrival airport + time, duration, stops
    - Return segments (for round trips, same format)
  - "Showing X results" count
3. **Price grid view** (toggle from list):
  - For one-way: table of departure date vs. price (cheapest per date)
  - For round-trip: 2D grid of departure date (rows) × return date (columns) with price in each cell, color-coded from green (cheapest) to red (most expensive)
4. **Responsive design**: works on desktop and tablet (min-width 768px)

## Non-Functional Requirements

- **Performance**: search results returned within 5 seconds for typical requests (Amadeus test API latency included)
- **Security**: API keys never exposed to frontend; all Amadeus calls made server-side only; input validation on both frontend and backend
- **Accessibility**: form labels and ARIA attributes for screen readers; keyboard-navigable search form
- **Error resilience**: frontend gracefully handles network errors and API unavailability

## Success Criteria

- User can successfully search one-way flights with a departure date range and see results
- User can successfully search round-trip flights with departure and return date ranges and see results
- Price grid renders correctly for both one-way (1D) and round-trip (2D) searches
- Airport autocomplete returns suggestions within 1 second of typing 3+ characters
- Backend validates all inputs and returns appropriate 4xx errors for invalid data
- Backend caches identical searches for 15 minutes
- All backend endpoints have pytest tests with ≥80% coverage
- Frontend form validation prevents searches with invalid date ranges (range > 30 days, departure in past)
- App is functional with both `AMADEUS_HOSTNAME=test` (sandbox) and production credentials
- Health check endpoint returns 200 OK

## Out of Scope

- User authentication / accounts (m02)
- Saving searches (m02)
- Price tracking over time / history (m02)
- Email alerts (m02)
- Multi-city trips
- Cabin class selection
- Mobile (< 768px) optimization
- Deployment / hosting

## Dependencies

- External: Amadeus Self-Service API account (free tier) — user must provide `AMADEUS_CLIENT_ID` and `AMADEUS_CLIENT_SECRET` in `.env`
- Previous milestones: none (first milestone)

