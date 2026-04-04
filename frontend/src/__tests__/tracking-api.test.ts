/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getClientId, getAuthHeaders } from '../api/client';
import {
  createTrackedSearch,
  listTrackedSearches,
  deleteTrackedSearch,
  getPriceHistory,
} from '../api/tracking';
import type { TrackedSearch, PriceHistory, CreateTrackedSearchRequest } from '../types/tracking';

const mockFetch = vi.fn();
global.fetch = mockFetch;

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem(key: string) { return store[key] || null; },
    setItem(key: string, value: string) { store[key] = value.toString(); },
    clear() { store = {}; },
    removeItem(key: string) { delete store[key]; }
  };
})();
Object.defineProperty(global, 'localStorage', { value: localStorageMock });

beforeEach(() => {
  mockFetch.mockReset();
  localStorage.clear();
});

const mockTrackedSearch: TrackedSearch = {
  id: 'abc-123',
  client_id: 'client-456',
  origin: 'JFK',
  destination: 'LAX',
  trip_type: 'one_way',
  departure_date_from: '2024-06-01',
  departure_date_to: '2024-06-07',
  return_date_from: null,
  return_date_to: null,
  adults: 1,
  max_stops: null,
  threshold_price: '300.00',
  alert_email: 'test@example.com',
  created_at: '2024-05-01T00:00:00Z',
  is_active: true,
  current_best_price: null,
  last_checked_at: null,
};

describe('getClientId', () => {
  it('returns a UUID stored in localStorage', () => {
    const id = getClientId();
    expect(id).toBeTruthy();
    expect(localStorage.getItem('flight_tracker_client_id')).toBe(id);
    // Rough UUID format check
    expect(id).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it('returns the same UUID on subsequent calls (no new UUID generated)', () => {
    const id1 = getClientId();
    const id2 = getClientId();
    expect(id1).toBe(id2);
  });
});

describe('getAuthHeaders', () => {
  it('returns object with X-Client-ID key', () => {
    const headers = getAuthHeaders();
    expect(headers).toHaveProperty('X-Client-ID');
    expect(headers['X-Client-ID']).toBe(getClientId());
  });
});

describe('createTrackedSearch', () => {
  const body: CreateTrackedSearchRequest = {
    origin: 'JFK',
    destination: 'LAX',
    trip_type: 'one_way',
    departure_date_from: '2024-06-01',
    departure_date_to: '2024-06-07',
    return_date_from: null,
    return_date_to: null,
    adults: 1,
    max_stops: null,
    threshold_price: 300,
    alert_email: 'test@example.com',
  };

  it('sends POST to /api/v1/tracked-searches with correct headers and body, returns TrackedSearch', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockTrackedSearch,
    });

    const result = await createTrackedSearch(body);

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/tracked-searches');
    expect(options.method).toBe('POST');
    expect((options.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect((options.headers as Record<string, string>)['X-Client-ID']).toBeTruthy();
    expect(JSON.parse(options.body as string)).toEqual(body);
    expect(result).toEqual(mockTrackedSearch);
  });

  it('throws Error with detail message on non-OK response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: 'Validation error' }),
    });

    await expect(createTrackedSearch(body)).rejects.toThrow('Validation error');
  });
});

describe('listTrackedSearches', () => {
  it('sends GET with X-Client-ID header, returns TrackedSearch[]', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => [mockTrackedSearch],
    });

    const result = await listTrackedSearches();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/tracked-searches');
    expect((options.headers as Record<string, string>)['X-Client-ID']).toBeTruthy();
    expect(result).toEqual([mockTrackedSearch]);
  });

  it('throws on non-OK response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Server error' }),
    });

    await expect(listTrackedSearches()).rejects.toThrow('Server error');
  });
});

describe('deleteTrackedSearch', () => {
  it('sends DELETE to /api/v1/tracked-searches/{id} with X-Client-ID header', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });

    await deleteTrackedSearch('abc-123');

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/tracked-searches/abc-123');
    expect(options.method).toBe('DELETE');
    expect((options.headers as Record<string, string>)['X-Client-ID']).toBeTruthy();
  });

  it('throws on non-OK response', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Not found' }),
    });

    await expect(deleteTrackedSearch('bad-id')).rejects.toThrow('Not found');
  });
});

describe('getPriceHistory', () => {
  const mockHistory: PriceHistory = {
    tracked_search_id: 'abc-123',
    snapshots: [
      { checked_at: '2024-05-10T00:00:00Z', best_price: '250.00', currency: 'USD' },
    ],
  };

  it('sends GET to /api/v1/tracked-searches/{id}/history with X-Client-ID, returns PriceHistory', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockHistory,
    });

    const result = await getPriceHistory('abc-123');

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/tracked-searches/abc-123/history');
    expect((options.headers as Record<string, string>)['X-Client-ID']).toBeTruthy();
    expect(result).toEqual(mockHistory);
  });
});
