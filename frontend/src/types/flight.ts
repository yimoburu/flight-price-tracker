export interface SegmentInfo {
  airline: string;
  flight_number: string;
  departure_airport: string;
  departure_time: string;
  arrival_airport: string;
  arrival_time: string;
  duration: string;
  stops: number;
}

export interface FlightOfferResponse {
  price: string;
  currency: string;
  departure_date: string;
  return_date: string | null;
  outbound_segments: SegmentInfo[];
  return_segments: SegmentInfo[];
}

export interface AirportResult {
  iata_code: string;
  name: string;
  city: string;
  country: string;
}

export interface SearchParams {
  origin: AirportResult | null;
  destination: AirportResult | null;
  trip_type: 'one_way' | 'round_trip';
  departure_date_from: string;
  departure_date_to: string;
  return_date_from: string;
  return_date_to: string;
  adults: number;
  max_stops: number | null;
}
