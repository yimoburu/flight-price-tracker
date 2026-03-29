import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { HomePage } from './HomePage';
import type { FlightOfferResponse } from '../types/flight';
import { searchFlights } from '../api/search';

// Mock the searchFlights API
vi.mock('../api/search', () => ({
  searchFlights: vi.fn(),
}));

// Mock SearchForm to avoid complex AirportAutocomplete setup.
// Search params are defined inline to avoid vi.mock factory hoisting issues.
vi.mock('../components/SearchForm', () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  SearchForm: ({ onSearch, isLoading }: { onSearch: (p: any) => void; isLoading: boolean }) => (
    <button
      onClick={() =>
        onSearch({
          origin: { iata_code: 'JFK', name: 'John F Kennedy', city: 'New York', country: 'US' },
          destination: { iata_code: 'LHR', name: 'Heathrow', city: 'London', country: 'GB' },
          trip_type: 'one_way',
          departure_date_from: '2026-04-01',
          departure_date_to: '2026-04-07',
          return_date_from: '',
          return_date_to: '',
          adults: 1,
          max_stops: null,
        })
      }
      disabled={isLoading}
    >
      Search
    </button>
  ),
}));

const mockSegment = {
  airline: 'BA',
  flight_number: 'BA 123',
  departure_airport: 'LHR',
  departure_time: '2026-04-01T10:00:00',
  arrival_airport: 'JFK',
  arrival_time: '2026-04-01T15:30:00',
  duration: 'PT5H30M',
  stops: 0,
};

const mockOffer1: FlightOfferResponse = {
  price: '298.50',
  currency: 'USD',
  departure_date: '2026-04-01',
  return_date: null,
  outbound_segments: [mockSegment],
  return_segments: [],
};

const mockSearchFlights = vi.mocked(searchFlights);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('HomePage', () => {
  it('handleSearch calls searchFlights and updates status to success with results', async () => {
    mockSearchFlights.mockResolvedValueOnce([mockOffer1]);

    render(<HomePage />);

    const searchButton = screen.getByRole('button', { name: /search/i });
    fireEvent.click(searchButton);

    // searchFlights should have been called
    expect(mockSearchFlights).toHaveBeenCalled();

    // Wait for success state — results should appear
    await waitFor(() => {
      expect(screen.getByText('298.50')).toBeInTheDocument();
    });
  });

  it('handleSearch on error sets error state', async () => {
    mockSearchFlights.mockRejectedValueOnce(new Error('Rate limit exceeded'));

    render(<HomePage />);

    const searchButton = screen.getByRole('button', { name: /search/i });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText('Rate limit exceeded')).toBeInTheDocument();
    });
  });

  it('view toggle buttons not shown in idle state', () => {
    render(<HomePage />);

    expect(screen.queryByRole('button', { name: /list/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /grid/i })).not.toBeInTheDocument();
  });

  it('view toggle buttons appear after successful search with results', async () => {
    mockSearchFlights.mockResolvedValueOnce([mockOffer1]);

    render(<HomePage />);

    // Initially no toggle buttons
    expect(screen.queryByRole('button', { name: /list/i })).not.toBeInTheDocument();

    const searchButton = screen.getByRole('button', { name: /search/i });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /list/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /grid/i })).toBeInTheDocument();
    });
  });
});
