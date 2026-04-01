import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TrackedSearchesPage } from './TrackedSearchesPage';
import type { TrackedSearch } from '../types/tracking';

vi.mock('../api/tracking', () => ({
  listTrackedSearches: vi.fn(),
  deleteTrackedSearch: vi.fn(),
  getPriceHistory: vi.fn(),
}));

import { listTrackedSearches, deleteTrackedSearch } from '../api/tracking';

const mockListTrackedSearches = listTrackedSearches as ReturnType<typeof vi.fn>;
const mockDeleteTrackedSearch = deleteTrackedSearch as ReturnType<typeof vi.fn>;

const makeSearch = (id: string, origin: string, destination: string): TrackedSearch => ({
  id,
  client_id: 'client-1',
  origin,
  destination,
  trip_type: 'one_way',
  departure_date_from: '2026-06-01',
  departure_date_to: '2026-06-15',
  return_date_from: null,
  return_date_to: null,
  adults: 1,
  max_stops: null,
  threshold_price: '300.00',
  alert_email: 'user@example.com',
  created_at: '2026-03-01T00:00:00Z',
  is_active: true,
  current_best_price: '250.00',
  last_checked_at: '2026-03-28T12:00:00Z',
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, 'confirm').mockReturnValue(true);
});

describe('TrackedSearchesPage', () => {
  it('shows "Loading..." on mount', async () => {
    let resolve!: (value: TrackedSearch[]) => void;
    mockListTrackedSearches.mockReturnValue(new Promise((res) => { resolve = res; }));
    render(<TrackedSearchesPage />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    resolve([]);
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
  });

  it('shows error message when listTrackedSearches rejects', async () => {
    mockListTrackedSearches.mockRejectedValue(new Error('Server unavailable'));
    render(<TrackedSearchesPage />);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Server unavailable');
    });
  });

  it('shows "No tracked searches yet." when list is empty', async () => {
    mockListTrackedSearches.mockResolvedValue([]);
    render(<TrackedSearchesPage />);
    await waitFor(() => {
      expect(screen.getByText('No tracked searches yet.')).toBeInTheDocument();
    });
  });

  it('renders a row for each tracked search returned', async () => {
    const searches = [
      makeSearch('s1', 'SFO', 'JFK'),
      makeSearch('s2', 'LAX', 'ORD'),
    ];
    mockListTrackedSearches.mockResolvedValue(searches);
    render(<TrackedSearchesPage />);
    await waitFor(() => {
      expect(screen.getByText(/SFO/)).toBeInTheDocument();
      expect(screen.getByText(/LAX/)).toBeInTheDocument();
    });
  });

  it('removing a search via onDeleted removes it from the list', async () => {
    const searches = [
      makeSearch('s1', 'SFO', 'JFK'),
      makeSearch('s2', 'LAX', 'ORD'),
    ];
    mockListTrackedSearches.mockResolvedValue(searches);
    mockDeleteTrackedSearch.mockResolvedValue(undefined);
    render(<TrackedSearchesPage />);
    await waitFor(() => {
      expect(screen.getByText(/SFO/)).toBeInTheDocument();
    });
    // Delete the first row
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    fireEvent.click(deleteButtons[0]);
    await waitFor(() => {
      expect(screen.queryByText(/SFO/)).not.toBeInTheDocument();
      expect(screen.getByText(/LAX/)).toBeInTheDocument();
    });
  });
});
