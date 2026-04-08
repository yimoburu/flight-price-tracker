import { useEffect, useState } from 'react';
import type { TrackedSearch } from '../types/tracking';
import { listTrackedSearches } from '../api/tracking';
import { TrackedSearchRow } from '../components/TrackedSearchRow';

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
  if (searches.length === 0) return <p>No tracked searches yet.</p>;

  return (
    <div>
      <h1>My Tracked Searches</h1>
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
