import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PriceHistoryChart } from './index';
import type { PriceSnapshot } from '../../types/tracking';

const makeSnapshot = (date: string, price: string): PriceSnapshot => ({
  checked_at: `${date}T12:00:00Z`,
  best_price: price,
  currency: 'USD',
});

describe('PriceHistoryChart', () => {
  it('renders "No price data yet." when snapshots is empty array', () => {
    render(<PriceHistoryChart snapshots={[]} />);
    expect(screen.getByText('No price data yet.')).toBeInTheDocument();
  });

  it('does NOT render "No price data yet." when snapshots has 1 item', () => {
    const snapshots = [makeSnapshot('2026-04-01', '150.00')];
    render(<PriceHistoryChart snapshots={snapshots} />);
    expect(screen.queryByText('No price data yet.')).not.toBeInTheDocument();
  });

  it('does NOT render "No price data yet." when snapshots has 10 items', () => {
    const snapshots = Array.from({ length: 10 }, (_, i) =>
      makeSnapshot(`2026-04-${String(i + 1).padStart(2, '0')}`, String(100 + i * 10)),
    );
    render(<PriceHistoryChart snapshots={snapshots} />);
    expect(screen.queryByText('No price data yet.')).not.toBeInTheDocument();
  });

  it('renders a container element when snapshots has 1 item', () => {
    const snapshots = [makeSnapshot('2026-04-01', '150.00')];
    const { container } = render(<PriceHistoryChart snapshots={snapshots} />);
    expect(container.querySelector('div')).toBeInTheDocument();
  });

  it('renders a container element when snapshots has 10 items', () => {
    const snapshots = Array.from({ length: 10 }, (_, i) =>
      makeSnapshot(`2026-04-${String(i + 1).padStart(2, '0')}`, String(100 + i * 10)),
    );
    const { container } = render(<PriceHistoryChart snapshots={snapshots} />);
    expect(container.querySelector('div')).toBeInTheDocument();
  });

  it('does not crash with 0 data points', () => {
    expect(() => render(<PriceHistoryChart snapshots={[]} />)).not.toThrow();
  });

  it('does not crash with 1 data point', () => {
    const snapshots = [makeSnapshot('2026-04-01', '150.00')];
    expect(() => render(<PriceHistoryChart snapshots={snapshots} />)).not.toThrow();
  });

  it('does not crash with 10 data points', () => {
    const snapshots = Array.from({ length: 10 }, (_, i) =>
      makeSnapshot(`2026-04-${String(i + 1).padStart(2, '0')}`, String(100 + i * 10)),
    );
    expect(() => render(<PriceHistoryChart snapshots={snapshots} />)).not.toThrow();
  });
});
