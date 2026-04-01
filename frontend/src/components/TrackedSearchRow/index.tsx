import { useState } from 'react';
import type { TrackedSearch, PriceHistory } from '../../types/tracking';
import { deleteTrackedSearch, getPriceHistory } from '../../api/tracking';
import { PriceHistoryChart } from '../PriceHistoryChart';

interface TrackedSearchRowProps {
  search: TrackedSearch;
  onDeleted: (id: string) => void;
}

export function TrackedSearchRow({ search, onDeleted }: TrackedSearchRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [history, setHistory] = useState<PriceHistory | null>(null);
  const [historyStatus, setHistoryStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    if (!window.confirm('Delete this tracked search?')) return;
    try {
      await deleteTrackedSearch(search.id);
      onDeleted(search.id);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  async function handleToggleHistory() {
    const nowExpanded = !expanded;
    setExpanded(nowExpanded);
    if (nowExpanded && history === null) {
      setHistoryStatus('loading');
      try {
        const h = await getPriceHistory(search.id);
        setHistory(h);
        setHistoryStatus('idle');
      } catch {
        setHistoryStatus('error');
      }
    }
  }

  const thresholdDisplay = search.threshold_price;

  return (
    <div>
      <div>
        <span>{search.origin} → {search.destination}</span>
        <span>{search.trip_type === 'one_way' ? 'One Way' : 'Round Trip'}</span>
        <span>Departure: {search.departure_date_from} to {search.departure_date_to}</span>
        {search.trip_type === 'round_trip' && search.return_date_from && (
          <span>Return: {search.return_date_from} to {search.return_date_to}</span>
        )}
        <span>Threshold: {thresholdDisplay}</span>
        <span data-testid="best-price">Best price: <span>{search.current_best_price ?? '–'}</span></span>
        <span data-testid="last-checked">Last checked: <span>{search.last_checked_at ? new Date(search.last_checked_at).toLocaleDateString() : 'Never'}</span></span>
        <button aria-expanded={expanded} onClick={handleToggleHistory}>History</button>
        <button onClick={handleDelete}>Delete</button>
        {deleteError && <span role="alert">{deleteError}</span>}
      </div>
      {expanded && (
        <div>
          {historyStatus === 'loading' && <p>Loading history...</p>}
          {historyStatus === 'error' && <p>Failed to load history.</p>}
          {historyStatus === 'idle' && history && (
            <PriceHistoryChart snapshots={history.snapshots} />
          )}
        </div>
      )}
    </div>
  );
}
