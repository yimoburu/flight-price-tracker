import type { FlightOfferResponse, SegmentInfo } from '../../types/flight';

interface FlightCardProps {
  offer: FlightOfferResponse;
}

function parseDuration(d: string): string {
  const match = d.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
  const h = match?.[1] ?? '0';
  const m = match?.[2] ?? '0';
  return `${h}h ${m}m`;
}

function formatTime(isoString: string): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(isoString));
}

function stopsLabel(stops: number): string {
  if (stops === 0) return 'Nonstop';
  return `${stops} stop${stops > 1 ? 's' : ''}`;
}

function SegmentRow({ segment }: { segment: SegmentInfo }): JSX.Element {
  return (
    <div>
      <span>{segment.airline}</span>
      {' | '}
      <span>{segment.flight_number}</span>
      {' | '}
      <span>{segment.departure_airport}</span>
      {' '}
      <span>{formatTime(segment.departure_time)}</span>
      {' → '}
      <span>{segment.arrival_airport}</span>
      {' '}
      <span>{formatTime(segment.arrival_time)}</span>
      {' | '}
      <span>{parseDuration(segment.duration)}</span>
      {' | '}
      <span>{stopsLabel(segment.stops)}</span>
    </div>
  );
}

export function FlightCard({ offer }: FlightCardProps): JSX.Element {
  return (
    <article>
      <header>
        <strong>{offer.price}</strong> <span>{offer.currency}</span>
        {' — '}
        <span>{offer.departure_date}</span>
        {offer.return_date && <span> → {offer.return_date}</span>}
      </header>
      <section>
        <h3>Outbound</h3>
        {offer.outbound_segments.map((seg, i) => (
          <SegmentRow key={i} segment={seg} />
        ))}
      </section>
      {offer.return_segments.length > 0 && (
        <section>
          <h3>Return</h3>
          {offer.return_segments.map((seg, i) => (
            <SegmentRow key={i} segment={seg} />
          ))}
        </section>
      )}
    </article>
  );
}
