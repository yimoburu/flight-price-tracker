import { useState } from 'react';
import type { SearchParams, AirportResult } from '../../types/flight';
import { AirportAutocomplete } from '../AirportAutocomplete';

interface SearchFormProps {
  onSearch: (params: SearchParams) => void;
  isLoading: boolean;
}

export function SearchForm({ onSearch, isLoading }: SearchFormProps): JSX.Element {
  const [tripType, setTripType] = useState<'one_way' | 'round_trip'>('one_way');
  const [origin, setOrigin] = useState<AirportResult | null>(null);
  const [destination, setDestination] = useState<AirportResult | null>(null);
  const [depFrom, setDepFrom] = useState('');
  const [depTo, setDepTo] = useState('');
  const [retFrom, setRetFrom] = useState('');
  const [retTo, setRetTo] = useState('');
  const [adults, setAdults] = useState('1');
  const [maxStops, setMaxStops] = useState('');
  const [error, setError] = useState('');

  const today = new Date().toISOString().split('T')[0];
  const msPerDay = 86400000;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (!origin) {
      setError('Please select an origin airport.');
      return;
    }
    if (!destination) {
      setError('Please select a destination airport.');
      return;
    }
    if (origin.iata_code === destination.iata_code) {
      setError('Origin and destination cannot be the same.');
      return;
    }
    if (!depFrom || depFrom < today) {
      setError('Departure date cannot be in the past.');
      return;
    }
    if (!depTo || depTo < depFrom) {
      setError('Departure "to" date must be after "from" date.');
      return;
    }
    if ((new Date(depTo).getTime() - new Date(depFrom).getTime()) / msPerDay > 30) {
      setError('Departure date range cannot exceed 30 days.');
      return;
    }
    if (tripType === 'round_trip') {
      if (!retFrom || !retTo) {
        setError('Return dates are required for round trips.');
        return;
      }
      if (retFrom < depFrom) {
        setError('Return date must be on or after departure date.');
        return;
      }
      if ((new Date(retTo).getTime() - new Date(retFrom).getTime()) / msPerDay > 30) {
        setError('Return date range cannot exceed 30 days.');
        return;
      }
    }

    onSearch({
      origin,
      destination,
      trip_type: tripType,
      departure_date_from: depFrom,
      departure_date_to: depTo,
      return_date_from: retFrom,
      return_date_to: retTo,
      adults: Number(adults),
      max_stops: maxStops === '' ? null : Number(maxStops),
    });
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div>
        <button
          type="button"
          aria-pressed={tripType === 'one_way'}
          onClick={() => setTripType('one_way')}
        >
          One Way
        </button>
        <button
          type="button"
          aria-pressed={tripType === 'round_trip'}
          onClick={() => setTripType('round_trip')}
        >
          Round Trip
        </button>
      </div>
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={origin}
        onChange={setOrigin}
      />
      <AirportAutocomplete
        label="Destination"
        id="destination"
        value={destination}
        onChange={setDestination}
      />
      <div>
        <label htmlFor="dep-from">Departure from</label>
        <input
          type="date"
          id="dep-from"
          value={depFrom}
          min={today}
          onChange={(e) => setDepFrom(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="dep-to">Departure to</label>
        <input
          type="date"
          id="dep-to"
          value={depTo}
          min={today}
          onChange={(e) => setDepTo(e.target.value)}
        />
      </div>
      {tripType === 'round_trip' && (
        <>
          <div>
            <label htmlFor="ret-from">Return from</label>
            <input
              type="date"
              id="ret-from"
              value={retFrom}
              min={today}
              onChange={(e) => setRetFrom(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="ret-to">Return to</label>
            <input
              type="date"
              id="ret-to"
              value={retTo}
              min={today}
              onChange={(e) => setRetTo(e.target.value)}
            />
          </div>
        </>
      )}
      <div>
        <label htmlFor="adults">Adults</label>
        <select
          id="adults"
          value={adults}
          onChange={(e) => setAdults(e.target.value)}
        >
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="max-stops">Max stops</label>
        <select
          id="max-stops"
          value={maxStops}
          onChange={(e) => setMaxStops(e.target.value)}
        >
          <option value="">Any</option>
          <option value="0">Nonstop</option>
          <option value="1">1 stop</option>
        </select>
      </div>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={isLoading}>
        Search
      </button>
    </form>
  );
}
