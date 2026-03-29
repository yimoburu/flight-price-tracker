import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { ResultsList } from './index';
import type { FlightOfferResponse } from '../../types/flight';

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

const mockOffer: FlightOfferResponse = {
  price: '298.50',
  currency: 'USD',
  departure_date: '2026-04-01',
  return_date: null,
  outbound_segments: [mockSegment],
  return_segments: [],
};

describe('ResultsList', () => {
  it('loading state renders searching message', () => {
    render(<ResultsList status="loading" results={[]} errorMessage="" />);
    expect(screen.getByText(/searching/i)).toBeInTheDocument();
  });

  it('error state renders error message', () => {
    render(<ResultsList status="error" results={[]} errorMessage="Rate limit exceeded" />);
    expect(screen.getByText('Rate limit exceeded')).toBeInTheDocument();
  });

  it('empty results state renders no-results message', () => {
    render(<ResultsList status="success" results={[]} errorMessage="" />);
    expect(screen.getByText(/no flights found/i)).toBeInTheDocument();
  });

  it('results state renders correct count', () => {
    const offers = [mockOffer, mockOffer, mockOffer];
    render(<ResultsList status="success" results={offers} errorMessage="" />);
    expect(screen.getByText(/showing 3 result/i)).toBeInTheDocument();
  });

  it('FlightCard renders offer price and currency', () => {
    render(<ResultsList status="success" results={[mockOffer]} errorMessage="" />);
    expect(screen.getByText('298.50')).toBeInTheDocument();
    expect(screen.getByText('USD')).toBeInTheDocument();
  });

  it('FlightCard renders outbound segment details', () => {
    render(<ResultsList status="success" results={[mockOffer]} errorMessage="" />);
    expect(screen.getByText('BA 123')).toBeInTheDocument();
    expect(screen.getByText('LHR')).toBeInTheDocument();
    expect(screen.getByText('JFK')).toBeInTheDocument();
    expect(screen.getByText('Nonstop')).toBeInTheDocument();
  });

  it('FlightCard for one-way offer shows no return section', () => {
    render(<ResultsList status="success" results={[mockOffer]} errorMessage="" />);
    expect(screen.queryByText('Return')).not.toBeInTheDocument();
  });
});
