import { useEffect, useState } from 'react';
import type { TrackedSearch } from '../types/tracking';
import { listTrackedSearches } from '../api/tracking';
import { TrackedSearchRow } from '../components/TrackedSearchRow';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';
import { Link } from 'react-router-dom';

export function TrackedSearchesPage() {
  const [searches, setSearches] = useState<TrackedSearch[]>([]);
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    listTrackedSearches()
      .then((data) => {
        setSearches(data);
        setStatus('success');
      })
      .catch((err: Error) => {
        setErrorMessage(err.message);
        setStatus('error');
      });
  }, []);

  if (status === 'loading') return <p>Loading...</p>;
  if (status === 'error') return <p role="alert">{errorMessage}</p>;

  if (searches.length === 0) return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">My Tracked Searches</h1>
        <p className="text-sm text-neutral-500 mt-1">Prices checked automatically every hour</p>
      </div>
      <div className="flex flex-col items-center py-16 gap-4 text-center">
        <Search className="h-16 w-16 text-neutral-300" />
        <h2 className="text-xl font-semibold text-neutral-700">No tracked searches yet</h2>
        <p className="text-neutral-500 text-sm">Search for a flight and click &quot;Track this search&quot; to get started</p>
        <Button asChild variant="outline"><Link to="/">Search flights</Link></Button>
      </div>
    </>
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">My Tracked Searches</h1>
        <p className="text-sm text-neutral-500 mt-1">Prices checked automatically every hour</p>
      </div>
      {searches.map((s) => (
        <TrackedSearchRow
          key={s.id}
          search={s}
          onDeleted={(id) => setSearches((prev) => prev.filter((x) => x.id !== id))}
        />
      ))}
    </div>
  );
}
