import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PriceGrid, priceColor } from './index';
import type { FlightOfferResponse } from '../../types/flight';

const seg = {
  airline: 'BA',
  flight_number: 'BA 1',
  departure_airport: 'JFK',
  departure_time: '2026-04-01T10:00:00',
  arrival_airport: 'LHR',
  arrival_time: '2026-04-01T22:00:00',
  duration: 'PT12H',
  stops: 0,
};

// One-way offers: 3 offers, 2 dates
const oneWayOffers: FlightOfferResponse[] = [
  { price: '150.00', currency: 'USD', departure_date: '2026-04-01', return_date: null, outbound_segments: [seg], return_segments: [] },
  { price: '89.99',  currency: 'USD', departure_date: '2026-04-02', return_date: null, outbound_segments: [seg], return_segments: [] },
  { price: '120.00', currency: 'USD', departure_date: '2026-04-01', return_date: null, outbound_segments: [seg], return_segments: [] },
];

// Round-trip offers: covers [dep1,ret1] and [dep2,ret2] only
const rtOffers: FlightOfferResponse[] = [
  { price: '299.00', currency: 'USD', departure_date: '2026-04-01', return_date: '2026-04-15', outbound_segments: [seg], return_segments: [seg] },
  { price: '399.00', currency: 'USD', departure_date: '2026-04-08', return_date: '2026-04-22', outbound_segments: [seg], return_segments: [seg] },
];

describe('PriceGrid', () => {
  describe('one-way grid', () => {
    it('renders 2 data rows for 3 offers with 2 unique dates, showing cheapest per date', () => {
      render(<PriceGrid offers={oneWayOffers} tripType="one_way" />);
      // 2026-04-01 has offers 150.00 and 120.00 → cheapest is 120.00
      // 2026-04-02 has offer 89.99 → cheapest is 89.99
      const rows = screen.getAllByRole('row');
      // 1 header row + 2 data rows
      expect(rows).toHaveLength(3);
      expect(screen.getByText('120.00')).toBeInTheDocument();
      expect(screen.getByText('89.99')).toBeInTheDocument();
      expect(screen.queryByText('150.00')).not.toBeInTheDocument();
    });

    it('rows are sorted by date ascending', () => {
      render(<PriceGrid offers={oneWayOffers} tripType="one_way" />);
      const rowHeaders = screen.getAllByRole('rowheader');
      // First row header is the date header (th scope=row), sorted ascending
      const dates = rowHeaders.map(rh => rh.textContent);
      expect(dates[0]).toBe('2026-04-01');
      expect(dates[1]).toBe('2026-04-02');
    });

    it('renders column headers "Departure Date" and "Price"', () => {
      render(<PriceGrid offers={oneWayOffers} tripType="one_way" />);
      expect(screen.getByText('Departure Date')).toBeInTheDocument();
      expect(screen.getByText('Price')).toBeInTheDocument();
    });

    it('price cell has backgroundColor style applied', () => {
      render(<PriceGrid offers={oneWayOffers} tripType="one_way" />);
      // Find the cell with price 89.99 and check it has a background color
      const priceCell = screen.getByText('89.99').closest('td');
      expect(priceCell).not.toBeNull();
      expect(priceCell!.style.backgroundColor).toBeTruthy();
    });
  });

  describe('round-trip grid', () => {
    it('renders 2 row headers and 2 column headers for 2x2 unique dates', () => {
      render(<PriceGrid offers={rtOffers} tripType="round_trip" />);
      const columnHeaders = screen.getAllByRole('columnheader');
      // 1 corner header + 2 return date column headers = 3 col headers
      expect(columnHeaders).toHaveLength(3);
      // 2 departure date row headers
      const rowHeaders = screen.getAllByRole('rowheader');
      expect(rowHeaders).toHaveLength(2);
    });

    it('renders prices in cells for matched date pairs', () => {
      render(<PriceGrid offers={rtOffers} tripType="round_trip" />);
      expect(screen.getByText('299.00')).toBeInTheDocument();
      expect(screen.getByText('399.00')).toBeInTheDocument();
    });

    it('renders empty cell when no offer for a date pair', () => {
      render(<PriceGrid offers={rtOffers} tripType="round_trip" />);
      // 2x2 grid: 2026-04-01/2026-04-15 has price, 2026-04-08/2026-04-22 has price,
      // but 2026-04-01/2026-04-22 and 2026-04-08/2026-04-15 are empty
      const rows = screen.getAllByRole('row');
      // row[0] = header, row[1] = dep 2026-04-01, row[2] = dep 2026-04-08
      const dataRow1 = rows[1];
      const cells = dataRow1.querySelectorAll('td');
      // cells[0] = ret 2026-04-15 (has price 299.00), cells[1] = ret 2026-04-22 (empty)
      expect(cells[0].textContent).toBe('299.00');
      expect(cells[1].textContent).toBe('');
    });

    it('returns empty div when offers array is empty', () => {
      const { container } = render(<PriceGrid offers={[]} tripType="one_way" />);
      const div = container.querySelector('div');
      expect(div).toBeInTheDocument();
      expect(container.querySelector('table')).toBeNull();
    });
  });

  describe('priceColor utility', () => {
    it('priceColor(100, 100, 200) contains "120" (min price → green hue=120)', () => {
      const result = priceColor(100, 100, 200);
      expect(result).toContain('120');
    });

    it('priceColor(200, 100, 200) starts with "hsl(0" (max price → red hue=0)', () => {
      const result = priceColor(200, 100, 200);
      expect(result.startsWith('hsl(0')).toBe(true);
    });

    it('priceColor(150, 150, 150) returns valid hsl string (all-same prices → green)', () => {
      const result = priceColor(150, 150, 150);
      expect(result).toMatch(/^hsl\(\d+, 70%, 45%\)$/);
      expect(result).not.toContain('NaN');
      // When all same price, should return green (hue=120)
      expect(result).toBe('hsl(120, 70%, 45%)');
    });

    it('priceColor midpoint returns hsl with hue near 60', () => {
      // price=150, min=100, max=200 → ratio=0.5, hue=120-60=60
      const result = priceColor(150, 100, 200);
      expect(result).toBe('hsl(60, 70%, 45%)');
    });
  });
});
