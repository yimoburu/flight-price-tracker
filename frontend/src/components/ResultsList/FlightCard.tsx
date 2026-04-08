import type { FlightOfferResponse, SegmentInfo } from '../../types/flight';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

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

function SegmentRow({ segment }: { segment: SegmentInfo }): JSX.Element {
  const stops = segment.stops;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-neutral-500">{segment.airline}</span>
      <span className="text-sm text-neutral-500">{segment.flight_number}</span>
      <span className="text-xl font-semibold">{segment.departure_airport}</span>
      <span className="text-base text-neutral-900">{formatTime(segment.departure_time)}</span>
      <span className="text-sm text-neutral-500">→</span>
      <span className="text-xl font-semibold">{segment.arrival_airport}</span>
      <span className="text-base text-neutral-900">{formatTime(segment.arrival_time)}</span>
      <span className="text-sm text-neutral-500">{parseDuration(segment.duration)}</span>
      {stops === 0
        ? <Badge className="bg-green-100 text-green-700 border-0">Nonstop</Badge>
        : <Badge className="bg-amber-100 text-amber-700 border-0">{stops} stop{stops > 1 ? 's' : ''}</Badge>
      }
    </div>
  );
}

export function FlightCard({ offer }: FlightCardProps): JSX.Element {
  return (
    <Card className="mb-4 hover:shadow-md transition-shadow">
      <CardContent className="p-4">
        <article>
          <div className="flex justify-between items-start mb-3">
            <div>
              <span className="text-sm text-neutral-500">{offer.departure_date}</span>
              {offer.return_date && <span className="text-sm text-neutral-500"> → {offer.return_date}</span>}
            </div>
            <div>
              <span className="text-2xl font-bold text-sky-600">{offer.price}</span>
              <span className="text-sm text-neutral-500 ml-1">{offer.currency}</span>
            </div>
          </div>
          <section>
            <h3 className="text-sm font-medium text-neutral-700 mb-2">Outbound</h3>
            {offer.outbound_segments.map((seg, i) => (
              <SegmentRow key={i} segment={seg} />
            ))}
          </section>
          {offer.return_segments.length > 0 && (
            <>
              <Separator className="my-3" />
              <section>
                <h3 className="text-sm font-medium text-neutral-700 mb-2">Return</h3>
                {offer.return_segments.map((seg, i) => (
                  <SegmentRow key={i} segment={seg} />
                ))}
              </section>
            </>
          )}
        </article>
      </CardContent>
    </Card>
  );
}
