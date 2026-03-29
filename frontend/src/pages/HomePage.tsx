import { useState } from 'react';
import { SearchForm } from '../components/SearchForm';
import { ResultsList } from '../components/ResultsList';
import { PriceGrid } from '../components/PriceGrid';
import { searchFlights } from '../api/search';
import type { SearchParams } from '../types/flight';
import type { FlightOfferResponse } from '../types/flight';

export function HomePage() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [results, setResults] = useState<FlightOfferResponse[]>([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [tripType, setTripType] = useState<'one_way' | 'round_trip'>('one_way');

  async function handleSearch(params: SearchParams) {
    setStatus('loading');
    setResults([]);
    setErrorMessage('');
    // extract tripType from params for PriceGrid
    setTripType(params.trip_type);
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
    <main>
      <h1>Flight Price Tracker</h1>
      <SearchForm onSearch={handleSearch} isLoading={status === 'loading'} />
      {status === 'success' && results.length > 0 && (
        <div>
          <button onClick={() => setViewMode('list')} aria-pressed={viewMode === 'list'}>List</button>
          <button onClick={() => setViewMode('grid')} aria-pressed={viewMode === 'grid'}>Grid</button>
        </div>
      )}
      {viewMode === 'list' || status !== 'success'
        ? <ResultsList status={status} results={results} errorMessage={errorMessage} />
        : <PriceGrid offers={results} tripType={tripType} />
      }
    </main>
  );
}
