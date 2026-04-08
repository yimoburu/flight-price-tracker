import type { FlightOfferResponse } from '../../types/flight';
import { FlightCard } from './FlightCard';
import { LayoutList, LayoutGrid } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

type SearchStatus = 'idle' | 'loading' | 'success' | 'error';

interface ResultsListProps {
  status: SearchStatus;
  results: FlightOfferResponse[];
  errorMessage: string;
  viewMode?: 'list' | 'grid';
  onViewModeChange?: (mode: 'list' | 'grid') => void;
}

export function ResultsList({ status, results, errorMessage, viewMode = 'list', onViewModeChange }: ResultsListProps): JSX.Element {
  if (status === 'idle') return <div />;

  if (status === 'loading') {
    return (
      <div role="status" aria-live="polite">
        <span className="sr-only">Searching for flights...</span>
        <div aria-hidden="true" className="flex flex-col gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="rounded-lg border border-neutral-200 p-6">
              <div className="flex justify-between mb-4">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-8 w-20" />
              </div>
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div role="alert" aria-live="polite">
        {errorMessage}
      </div>
    );
  }

  const count = results.length;
  const plural = count !== 1 ? 's' : '';

  return (
    <div aria-live="polite">
      {results.length === 0 ? (
        <p>No flights found for this route and date range.</p>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-neutral-500">Showing {count} result{plural}</p>
            {onViewModeChange && (
              <div className="flex gap-1">
                <button
                  onClick={() => onViewModeChange('list')}
                  aria-pressed={viewMode === 'list'}
                  aria-label="List view"
                  className={`p-2 rounded ${viewMode === 'list' ? 'bg-sky-100 text-sky-600' : 'text-neutral-400 hover:text-neutral-600'}`}
                >
                  <LayoutList className="h-4 w-4" />
                </button>
                <button
                  onClick={() => onViewModeChange('grid')}
                  aria-pressed={viewMode === 'grid'}
                  aria-label="Grid view"
                  className={`p-2 rounded ${viewMode === 'grid' ? 'bg-sky-100 text-sky-600' : 'text-neutral-400 hover:text-neutral-600'}`}
                >
                  <LayoutGrid className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
          <ul>
            {results.map((offer, i) => (
              <li key={i}>
                <FlightCard offer={offer} />
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
