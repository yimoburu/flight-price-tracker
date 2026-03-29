import type { FlightOfferResponse } from '../../types/flight';
import { FlightCard } from './FlightCard';

type SearchStatus = 'idle' | 'loading' | 'success' | 'error';

interface ResultsListProps {
  status: SearchStatus;
  results: FlightOfferResponse[];
  errorMessage: string;
}

export function ResultsList({ status, results, errorMessage }: ResultsListProps): JSX.Element {
  if (status === 'idle') return <div />;

  if (status === 'loading') {
    return (
      <div role="status" aria-live="polite">
        <span>Searching for flights...</span>
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

  return (
    <div aria-live="polite">
      {results.length === 0 ? (
        <p>No flights found for this route and date range.</p>
      ) : (
        <>
          <p>Showing {results.length} result{results.length !== 1 ? 's' : ''}</p>
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
