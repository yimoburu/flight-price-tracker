import type { AirportResult } from '../types/flight';

export async function searchAirports(query: string): Promise<AirportResult[]> {
  const res = await fetch(`/api/v1/airports?q=${encodeURIComponent(query)}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<AirportResult[]>;
}
