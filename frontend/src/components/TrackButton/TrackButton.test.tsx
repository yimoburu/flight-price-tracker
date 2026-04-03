import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TrackButton } from './index';
import { createTrackedSearch } from '../../api/tracking';
import type { SearchParams } from '../../types/flight';

vi.mock('../../api/tracking', () => ({
  createTrackedSearch: vi.fn(),
}));

const mockCreateTrackedSearch = vi.mocked(createTrackedSearch);

function makeSearchParams(): SearchParams {
  return {
    origin: { iata_code: 'JFK', name: 'John F Kennedy', city: 'New York', country: 'US' },
    destination: { iata_code: 'LHR', name: 'Heathrow', city: 'London', country: 'GB' },
    trip_type: 'one_way',
    departure_date_from: '2026-04-01',
    departure_date_to: '2026-04-07',
    return_date_from: '',
    return_date_to: '',
    adults: 1,
    max_stops: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('TrackButton', () => {
  it('renders "Track this search" button when not tracking', () => {
    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    expect(screen.getByRole('button', { name: /track this search/i })).toBeInTheDocument();
  });

  it('clicking the button opens the modal (dialog is visible)', () => {
    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('Cancel button closes the modal', () => {
    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows validation error when email is empty on Save', () => {
    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    // Leave email empty, set a valid threshold
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/valid email/i);
  });

  it('shows validation error when threshold is 0 or negative on Save', () => {
    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    fireEvent.change(screen.getByLabelText(/alert email/i), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/price greater than 0/i);
  });

  it('shows validation error when email is invalid format on Save', () => {
    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    fireEvent.change(screen.getByLabelText(/alert email/i), { target: { value: 'not-an-email' } });
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(/valid email/i);
  });

  it('calls createTrackedSearch with correct body on valid submit', async () => {
    const mockResult = { id: 'abc', client_id: 'cid', origin: 'JFK', destination: 'LHR' } as any;
    mockCreateTrackedSearch.mockResolvedValueOnce(mockResult);

    const params = makeSearchParams();
    render(<TrackButton searchParams={params} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    fireEvent.change(screen.getByLabelText(/alert email/i), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '299.99' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(mockCreateTrackedSearch).toHaveBeenCalledWith({
        origin: 'JFK',
        destination: 'LHR',
        trip_type: 'one_way',
        departure_date_from: '2026-04-01',
        departure_date_to: '2026-04-07',
        return_date_from: null,
        return_date_to: null,
        adults: 1,
        max_stops: null,
        threshold_price: 299.99,
        alert_email: 'user@example.com',
      });
    });
  });

  it('after successful save, modal closes and button becomes disabled "Tracking"', async () => {
    const mockResult = { id: 'abc', client_id: 'cid', origin: 'JFK', destination: 'LHR' } as any;
    mockCreateTrackedSearch.mockResolvedValueOnce(mockResult);

    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    fireEvent.change(screen.getByLabelText(/alert email/i), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    const trackingBtn = screen.getByRole('button', { name: /tracking/i });
    expect(trackingBtn).toBeDisabled();
  });

  it('shows API error message inside modal on createTrackedSearch rejection', async () => {
    mockCreateTrackedSearch.mockRejectedValueOnce(new Error('Service unavailable'));

    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    fireEvent.change(screen.getByLabelText(/alert email/i), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/service unavailable/i);
    });
  });

  it('does not close modal on API error', async () => {
    mockCreateTrackedSearch.mockRejectedValueOnce(new Error('Network error'));

    render(<TrackButton searchParams={makeSearchParams()} currency="USD" />);
    fireEvent.click(screen.getByRole('button', { name: /track this search/i }));

    fireEvent.change(screen.getByLabelText(/alert email/i), { target: { value: 'user@example.com' } });
    fireEvent.change(screen.getByLabelText(/price threshold/i), { target: { value: '200' } });
    fireEvent.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
});
