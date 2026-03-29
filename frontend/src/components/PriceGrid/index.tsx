import type { FlightOfferResponse } from '../../types/flight';

interface PriceGridProps {
  offers: FlightOfferResponse[];
  tripType: 'one_way' | 'round_trip';
}

export function priceColor(price: number, min: number, max: number): string {
  if (max === min) return 'hsl(120, 70%, 45%)';
  const ratio = (price - min) / (max - min);
  const hue = Math.round(120 - ratio * 120);
  return `hsl(${hue}, 70%, 45%)`;
}

export function PriceGrid({ offers, tripType }: PriceGridProps): JSX.Element {
  if (offers.length === 0) return <div />;

  if (tripType === 'one_way') {
    // Build Map<departure_date, cheapest_price>
    const priceMap = new Map<string, number>();
    for (const offer of offers) {
      const dep = String(offer.departure_date);
      const price = parseFloat(offer.price);
      if (!priceMap.has(dep) || price < priceMap.get(dep)!) {
        priceMap.set(dep, price);
      }
    }
    const dates = [...priceMap.keys()].sort();
    const prices = [...priceMap.values()];
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);

    return (
      <table>
        <thead>
          <tr>
            <th scope="col">Departure Date</th>
            <th scope="col">Price</th>
          </tr>
        </thead>
        <tbody>
          {dates.map(dep => {
            const price = priceMap.get(dep)!;
            return (
              <tr key={dep}>
                <th scope="row">{dep}</th>
                <td style={{ backgroundColor: priceColor(price, minPrice, maxPrice), color: '#fff' }}>
                  {price.toFixed(2)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  // Round-trip: 2D grid
  // Build Map<`${dep}:${ret}`, cheapest_price>
  const priceMap = new Map<string, number>();
  const depDates = new Set<string>();
  const retDates = new Set<string>();
  for (const offer of offers) {
    const dep = String(offer.departure_date);
    const ret = String(offer.return_date ?? '');
    if (!ret) continue;
    depDates.add(dep);
    retDates.add(ret);
    const key = `${dep}:${ret}`;
    const price = parseFloat(offer.price);
    if (!priceMap.has(key) || price < priceMap.get(key)!) {
      priceMap.set(key, price);
    }
  }
  const sortedDeps = [...depDates].sort();
  const sortedRets = [...retDates].sort();
  const allPrices = [...priceMap.values()];
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);

  return (
    <table>
      <thead>
        <tr>
          <th scope="col">Dep \ Ret</th>
          {sortedRets.map(ret => <th key={ret} scope="col">{ret}</th>)}
        </tr>
      </thead>
      <tbody>
        {sortedDeps.map(dep => (
          <tr key={dep}>
            <th scope="row">{dep}</th>
            {sortedRets.map(ret => {
              const key = `${dep}:${ret}`;
              const price = priceMap.get(key);
              return (
                <td key={ret} style={price !== undefined ? {
                  backgroundColor: priceColor(price, minPrice, maxPrice),
                  color: '#fff',
                } : {}}>
                  {price !== undefined ? price.toFixed(2) : ''}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
