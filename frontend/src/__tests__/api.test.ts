import { describe, it, expect, vi, beforeEach } from 'vitest';
import { searchAirports } from '../api/airports';
import { searchFlights } from '../api/search';
import type { SearchParams } from '../types/flight';

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

describe('searchAirports', () => {
  it('returns airport results on success', async () => {
    const mockData = [
      { iata_code: 'JFK', name: 'John F. Kennedy', city: 'New York', country: 'US' },
    ];
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });
    const result = await searchAirports('JFK');
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/airports?q=JFK');
    expect(result).toEqual(mockData);
  });

  it('throws Error with detail message on non-2xx', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Query too short' }),
    });
    await expect(searchAirports('x')).rejects.toThrow('Query too short');
  });

  it('throws fallback HTTP error when no detail field', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    await expect(searchAirports('x')).rejects.toThrow('HTTP 500');
  });

  it('URL-encodes the query parameter', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => [] });
    await searchAirports('New York');
    expect(mockFetch).toHaveBeenCalledWith('/api/v1/airports?q=New%20York');
  });
});

describe('searchFlights', () => {
  const params: SearchParams = {
    origin: { iata_code: 'JFK', name: 'JFK', city: 'NY', country: 'US' },
    destination: { iata_code: 'LAX', name: 'LAX', city: 'LA', country: 'US' },
    trip_type: 'one_way',
    departure_date_from: '2024-06-01',
    departure_date_to: '2024-06-07',
    return_date_from: '',
    return_date_to: '',
    adults: 1,
    max_stops: null,
  };

  it('returns flight offers on success', async () => {
    const mockData = [
      {
        price: '199.00',
        currency: 'USD',
        departure_date: '2024-06-01',
        return_date: null,
        outbound_segments: [],
        return_segments: [],
      },
    ];
    mockFetch.mockResolvedValue({ ok: true, json: async () => mockData });
    const result = await searchFlights(params);
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v1/search',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(result).toEqual(mockData);
  });

  it('sends JSON body with snake_case keys', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => [] });
    await searchFlights(params);
    const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    const body = JSON.parse(options.body as string) as Record<string, unknown>;
    expect(body).toHaveProperty('trip_type', 'one_way');
    expect(body).toHaveProperty('departure_date_from', '2024-06-01');
  });

  it('throws Error with detail on non-2xx', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Invalid origin' }),
    });
    await expect(searchFlights(params)).rejects.toThrow('Invalid origin');
  });
});
