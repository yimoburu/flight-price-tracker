import type { SearchParams, FlightOfferResponse } from '../types/flight';

export async function searchFlights(params: SearchParams): Promise<FlightOfferResponse[]> {
  const payload = {
    ...params,
    origin: params.origin?.iata_code,
    destination: params.destination?.iata_code,
    return_date_from: params.return_date_from || null,
    return_date_to: params.return_date_to || null,
  };

  const res = await fetch('/api/v1/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: any };
    let errorMessage = `HTTP ${res.status}`;
    if (Array.isArray(body.detail)) {
      errorMessage = body.detail.map((e: any) => `${e.loc?.join('.') || 'field'}: ${e.msg || JSON.stringify(e)}`).join(', ');
    } else if (body.detail) {
      errorMessage = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
    }
    throw new Error(errorMessage);
  }
  return res.json() as Promise<FlightOfferResponse[]>;
}
