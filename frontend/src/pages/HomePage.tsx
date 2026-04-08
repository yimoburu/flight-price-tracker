import { useState } from 'react';
import { SearchForm } from '../components/SearchForm';
import { ResultsList } from '../components/ResultsList';
import { PriceGrid } from '../components/PriceGrid';
import { TrackButton } from '../components/TrackButton';
import { searchFlights } from '../api/search';
import type { SearchParams } from '../types/flight';
import type { FlightOfferResponse } from '../types/flight';

export function HomePage() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [results, setResults] = useState<FlightOfferResponse[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [tripType, setTripType] = useState<'one_way' | 'round_trip'>('one_way');
  const [searchParams, setSearchParams] = useState<SearchParams | null>(null);

  async function handleSearch(params: SearchParams) {
    setStatus('loading');
    setResults([]);
    setErrorMessage('');
    // extract tripType from params for PriceGrid
    setTripType(params.trip_type);
    setSearchParams(params);
    try {
      const data = await searchFlights(params);
      setStatus('success');
      setResults(data);
    } catch (err) {
      setStatus('error');
      setErrorMessage(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  return (
    <div>
      <h1>Flight Price Tracker</h1>
      <SearchForm onSearch={handleSearch} isLoading={status === 'loading'} />
      {viewMode === 'list' || status !== 'success'
        ? <ResultsList
            status={status}
            results={results}
            errorMessage={errorMessage}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        : <PriceGrid offers={results} tripType={tripType} />
      }
      {status === 'success' && results.length > 0 && (
        <div className="sticky bottom-0 bg-white border-t border-neutral-200 py-3 flex justify-end">
          <TrackButton searchParams={searchParams!} currency={results[0]?.currency ?? 'USD'} />
        </div>
      )}
    </div>
  );
}
