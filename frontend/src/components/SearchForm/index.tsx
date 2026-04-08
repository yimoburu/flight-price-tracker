import { useState } from 'react';
import type { SearchParams, AirportResult } from '../../types/flight';
import { AirportAutocomplete } from '../AirportAutocomplete';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { Loader2 } from 'lucide-react';

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
    <Card className="w-full">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg font-semibold">Find Flights</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">

          {/* Trip type toggle */}
          <div className="flex gap-1 p-1 bg-neutral-100 rounded-full w-fit">
            <button type="button" aria-pressed={tripType === 'one_way'}
              onClick={() => setTripType('one_way')}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                tripType === 'one_way'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-neutral-700 hover:text-neutral-900'
              }`}>One Way</button>
            <button type="button" aria-pressed={tripType === 'round_trip'}
              onClick={() => setTripType('round_trip')}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                tripType === 'round_trip'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-neutral-700 hover:text-neutral-900'
              }`}>Round Trip</button>
          </div>

          {/* Airport row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <AirportAutocomplete label="Origin" id="origin" value={origin} onChange={setOrigin} />
            <AirportAutocomplete label="Destination" id="destination" value={destination} onChange={setDestination} />
          </div>

          {/* Departure date row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label htmlFor="dep-from" className="text-sm font-medium text-neutral-700">Departure from</label>
              <input type="date" id="dep-from" value={depFrom} min={today}
                onChange={(e) => setDepFrom(e.target.value)}
                className="border border-neutral-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="dep-to" className="text-sm font-medium text-neutral-700">Departure to</label>
              <input type="date" id="dep-to" value={depTo} min={today}
                onChange={(e) => setDepTo(e.target.value)}
                className="border border-neutral-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
            </div>
          </div>

          {/* Return date row — ALWAYS rendered, hidden via visibility */}
          <div className={`grid grid-cols-2 gap-4 transition-all duration-200 ${
            tripType === 'one_way'
              ? 'invisible opacity-0 pointer-events-none h-0 overflow-hidden'
              : 'visible opacity-100'
          }`}>
            <div className="flex flex-col gap-1">
              <label htmlFor="ret-from" className="text-sm font-medium text-neutral-700">Return from</label>
              <input type="date" id="ret-from" value={retFrom} min={today}
                onChange={(e) => setRetFrom(e.target.value)}
                className="border border-neutral-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="ret-to" className="text-sm font-medium text-neutral-700">Return to</label>
              <input type="date" id="ret-to" value={retTo} min={today}
                onChange={(e) => setRetTo(e.target.value)}
                className="border border-neutral-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
            </div>
          </div>

          {/* Adults + Max Stops row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label htmlFor="adults" className="text-sm font-medium text-neutral-700">Adults</label>
              <select id="adults" value={adults} onChange={(e) => setAdults(e.target.value)}
                className="border border-neutral-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="max-stops" className="text-sm font-medium text-neutral-700">Max stops</label>
              <select id="max-stops" value={maxStops} onChange={(e) => setMaxStops(e.target.value)}
                className="border border-neutral-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400">
                <option value="">Any</option>
                <option value="0">Nonstop</option>
                <option value="1">1 stop</option>
              </select>
            </div>
          </div>

          {error && <p role="alert" className="text-sm text-red-500">{error}</p>}

          <button type="submit" disabled={isLoading}
            className="w-full h-12 bg-sky-600 hover:bg-sky-700 disabled:opacity-60 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors">
            {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
            Search
          </button>
        </form>
      </CardContent>
    </Card>
  );
}
