import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TrackedSearchRow } from './index';
import type { TrackedSearch, PriceHistory } from '../../types/tracking';

vi.mock('../../api/tracking', () => ({
  deleteTrackedSearch: vi.fn(),
  getPriceHistory: vi.fn(),
}));

import { deleteTrackedSearch, getPriceHistory } from '../../api/tracking';

const mockDeleteTrackedSearch = deleteTrackedSearch as ReturnType<typeof vi.fn>;
const mockGetPriceHistory = getPriceHistory as ReturnType<typeof vi.fn>;

const baseSearch: TrackedSearch = {
  id: 'search-1',
  client_id: 'client-1',
  origin: 'SFO',
  destination: 'JFK',
  trip_type: 'one_way',
  departure_date_from: '2026-06-01',
  departure_date_to: '2026-06-15',
  return_date_from: null,
  return_date_to: null,
  adults: 1,
  max_stops: null,
  threshold_price: '350.00',
  alert_email: 'user@example.com',
  created_at: '2026-03-01T00:00:00Z',
  is_active: true,
  current_best_price: '299.00',
  last_checked_at: '2026-03-28T12:00:00Z',
};

const roundTripSearch: TrackedSearch = {
  ...baseSearch,
  id: 'search-2',
  trip_type: 'round_trip',
  return_date_from: '2026-06-20',
  return_date_to: '2026-06-30',
};

const mockHistory: PriceHistory = {
  tracked_search_id: 'search-1',
  snapshots: [
    { checked_at: '2026-03-28T12:00:00Z', best_price: '299.00', currency: 'USD' },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, 'confirm').mockReturnValue(true);
});

describe('TrackedSearchRow', () => {
  it('renders origin, destination, trip type, and departure dates', () => {
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    expect(screen.getByText(/SFO/)).toBeInTheDocument();
    expect(screen.getByText(/JFK/)).toBeInTheDocument();
    expect(screen.getByText(/One Way/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-06-01/)).toBeInTheDocument();
    expect(screen.getByText(/2026-06-15/)).toBeInTheDocument();
  });

  it('shows "–" for current_best_price when null', () => {
    const search = { ...baseSearch, current_best_price: null };
    render(<TrackedSearchRow search={search} onDeleted={vi.fn()} />);
    expect(screen.getByText('–')).toBeInTheDocument();
  });

  it('shows "Never" for last_checked_at when null', () => {
    const search = { ...baseSearch, last_checked_at: null };
    render(<TrackedSearchRow search={search} onDeleted={vi.fn()} />);
    expect(screen.getByText('Never')).toBeInTheDocument();
  });

  it('shows round trip label and return dates for round_trip', () => {
    render(<TrackedSearchRow search={roundTripSearch} onDeleted={vi.fn()} />);
    expect(screen.getByText(/Round Trip/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-06-20/)).toBeInTheDocument();
    expect(screen.getByText(/2026-06-30/)).toBeInTheDocument();
  });

  it('delete button calls window.confirm and deleteTrackedSearch on confirm', async () => {
    mockDeleteTrackedSearch.mockResolvedValue(undefined);
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(window.confirm).toHaveBeenCalledWith('Delete this tracked search?');
    await waitFor(() => {
      expect(mockDeleteTrackedSearch).toHaveBeenCalledWith('search-1');
    });
  });

  it('onDeleted callback called after successful delete', async () => {
    mockDeleteTrackedSearch.mockResolvedValue(undefined);
    const onDeleted = vi.fn();
    render(<TrackedSearchRow search={baseSearch} onDeleted={onDeleted} />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    await waitFor(() => {
      expect(onDeleted).toHaveBeenCalledWith('search-1');
    });
  });

  it('does not call deleteTrackedSearch when confirm is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(mockDeleteTrackedSearch).not.toHaveBeenCalled();
  });

  it('shows delete error inline when API throws', async () => {
    mockDeleteTrackedSearch.mockRejectedValue(new Error('Server error'));
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Server error');
    });
  });

  it('history button has aria-expanded false initially', () => {
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    const historyBtn = screen.getByRole('button', { name: /history/i });
    expect(historyBtn).toHaveAttribute('aria-expanded', 'false');
  });

  it('history button toggles aria-expanded on click', async () => {
    mockGetPriceHistory.mockResolvedValue(mockHistory);
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    const historyBtn = screen.getByRole('button', { name: /history/i });
    fireEvent.click(historyBtn);
    expect(historyBtn).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(historyBtn);
    expect(historyBtn).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows "Loading history..." while getPriceHistory is in flight', async () => {
    let resolveHistory!: (value: PriceHistory) => void;
    const historyPromise = new Promise<PriceHistory>((res) => {
      resolveHistory = res;
    });
    mockGetPriceHistory.mockReturnValue(historyPromise);
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /history/i }));
    expect(screen.getByText('Loading history...')).toBeInTheDocument();
    resolveHistory(mockHistory);
    await waitFor(() => {
      expect(screen.queryByText('Loading history...')).not.toBeInTheDocument();
    });
  });

  it('when expanded calls getPriceHistory and renders chart (no loading/error)', async () => {
    mockGetPriceHistory.mockResolvedValue(mockHistory);
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /history/i }));
    await waitFor(() => {
      expect(mockGetPriceHistory).toHaveBeenCalledWith('search-1');
      expect(screen.queryByText('Loading history...')).not.toBeInTheDocument();
      expect(screen.queryByText('Failed to load history.')).not.toBeInTheDocument();
    });
  });

  it('shows "Failed to load history." on getPriceHistory error', async () => {
    mockGetPriceHistory.mockRejectedValue(new Error('Network error'));
    render(<TrackedSearchRow search={baseSearch} onDeleted={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /history/i }));
    await waitFor(() => {
      expect(screen.getByText('Failed to load history.')).toBeInTheDocument();
    });
  });
});
