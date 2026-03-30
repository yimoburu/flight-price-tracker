import { getAuthHeaders } from './client';
import type { TrackedSearch, PriceHistory, CreateTrackedSearchRequest } from '../types/tracking';

export async function createTrackedSearch(body: CreateTrackedSearchRequest): Promise<TrackedSearch> {
  const res = await fetch('/api/v1/tracked-searches', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<TrackedSearch>;
}

export async function listTrackedSearches(): Promise<TrackedSearch[]> {
  const res = await fetch('/api/v1/tracked-searches', {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<TrackedSearch[]>;
}

export async function deleteTrackedSearch(id: string): Promise<void> {
  const res = await fetch(`/api/v1/tracked-searches/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
}

export async function getPriceHistory(id: string): Promise<PriceHistory> {
  const res = await fetch(`/api/v1/tracked-searches/${id}/history`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(data.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<PriceHistory>;
}
