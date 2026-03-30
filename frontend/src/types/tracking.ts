export interface TrackedSearch {
  id: string;
  client_id: string;
  origin: string;
  destination: string;
  trip_type: 'one_way' | 'round_trip';
  departure_date_from: string;
  departure_date_to: string;
  return_date_from: string | null;
  return_date_to: string | null;
  adults: number;
  max_stops: number | null;
  threshold_price: string;
  alert_email: string;
  created_at: string;
  is_active: boolean;
  current_best_price: string | null;
  last_checked_at: string | null;
}

export interface PriceSnapshot {
  checked_at: string;
  best_price: string;
  currency: string;
}

export interface PriceHistory {
  tracked_search_id: string;
  snapshots: PriceSnapshot[];
}

export interface CreateTrackedSearchRequest {
  origin: string;
  destination: string;
  trip_type: 'one_way' | 'round_trip';
  departure_date_from: string;
  departure_date_to: string;
  return_date_from: string | null;
  return_date_to: string | null;
  adults: number;
  max_stops: number | null;
  threshold_price: number;
  alert_email: string;
}
