import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { PriceSnapshot } from '../../types/tracking';

interface PriceHistoryChartProps {
  snapshots: PriceSnapshot[];
}

export function PriceHistoryChart({ snapshots }: PriceHistoryChartProps) {
  if (snapshots.length === 0) {
    return <p>No price data yet.</p>;
  }

  const chartData = snapshots.map((s) => ({
    date: s.checked_at.slice(0, 10),
    price: parseFloat(s.best_price),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis dataKey="price" />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="price" dot={true} />
      </LineChart>
    </ResponsiveContainer>
  );
}
