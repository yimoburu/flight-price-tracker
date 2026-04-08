import type { FlightOfferResponse } from '../../types/flight';

interface PriceGridProps {
  offers: FlightOfferResponse[];
  tripType: 'one_way' | 'round_trip';
}

export function priceTier(price: number, p25: number, p75: number): string {
  if (price <= p25) return 'bg-green-50 text-green-700';
  if (price >= p75) return 'bg-red-50 text-red-600';
  return 'bg-white text-neutral-900';
}

const thCls = 'bg-neutral-50 text-neutral-500 text-xs font-semibold p-2 border border-neutral-200 whitespace-nowrap';
const emptyTdCls = 'p-2 bg-neutral-50 border border-neutral-200';

function Legend({ currency }: { currency: string }) {
  return (
    <div className="flex gap-4 text-xs mb-3 text-neutral-600 items-center flex-wrap">
      <span className="font-medium text-neutral-700">Price range:</span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 h-4 rounded border border-green-200 bg-green-50 flex-shrink-0" />
        Lowest prices
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 h-4 rounded border border-neutral-200 bg-white flex-shrink-0" />
        Mid-range
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 h-4 rounded border border-red-200 bg-red-50 flex-shrink-0" />
        Highest prices
      </span>
      <span className="ml-auto text-neutral-500">All prices in {currency}</span>
    </div>
  );
}

export function PriceGrid({ offers, tripType }: PriceGridProps): JSX.Element {
  if (offers.length === 0) return <div />;

  const currency = offers[0]?.currency ?? 'USD';

  if (tripType === 'one_way') {
    const priceMap = new Map<string, number>();
    for (const offer of offers) {
      const dep = String(offer.departure_date);
      const price = parseFloat(offer.price);
      if (!priceMap.has(dep) || price < priceMap.get(dep)!) {
        priceMap.set(dep, price);
      }
    }
    const dates = [...priceMap.keys()].sort();
    const allPrices = [...priceMap.values()].sort((a, b) => a - b);
    const p25 = allPrices[Math.floor(allPrices.length * 0.25)];
    const p75 = allPrices[Math.floor(allPrices.length * 0.75)];

    return (
      <div>
        <Legend currency={currency} />
        <div className="overflow-x-auto">
          <table className="border-collapse text-sm w-full">
            <thead>
              <tr>
                <th scope="col" className={thCls}>Departure Date</th>
                <th scope="col" className={thCls}>Price</th>
              </tr>
            </thead>
            <tbody>
              {dates.map(dep => {
                const price = priceMap.get(dep)!;
                return (
                  <tr key={dep}>
                    <th scope="row" className={thCls}>{dep}</th>
                    <td className={`p-2 text-center font-medium border border-neutral-200 cursor-pointer hover:ring-2 hover:ring-sky-400 hover:ring-inset transition-all ${priceTier(price, p25, p75)}`}>
                      {price.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Round-trip: 2D grid
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
  const allPrices = [...priceMap.values()].sort((a, b) => a - b);
  const p25 = allPrices[Math.floor(allPrices.length * 0.25)];
  const p75 = allPrices[Math.floor(allPrices.length * 0.75)];

  return (
    <div>
      <Legend currency={currency} />
      <div className="overflow-x-auto">
        <table className="border-collapse text-sm w-full">
          <thead>
            <tr>
              <th scope="col" className={thCls}>Dep \ Ret</th>
              {sortedRets.map(ret => <th key={ret} scope="col" className={thCls}>{ret}</th>)}
            </tr>
          </thead>
          <tbody>
            {sortedDeps.map(dep => (
              <tr key={dep}>
                <th scope="row" className={thCls}>{dep}</th>
                {sortedRets.map(ret => {
                  const key = `${dep}:${ret}`;
                  const price = priceMap.get(key);
                  return price !== undefined ? (
                    <td key={ret} className={`p-2 text-center font-medium border border-neutral-200 cursor-pointer hover:ring-2 hover:ring-sky-400 hover:ring-inset transition-all ${priceTier(price, p25, p75)}`}>
                      {price.toFixed(2)}
                    </td>
                  ) : (
                    <td key={ret} className={emptyTdCls} />
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
