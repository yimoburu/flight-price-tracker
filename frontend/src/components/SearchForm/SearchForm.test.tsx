import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SearchForm } from './index';
import type { AirportResult, SearchParams } from '../../types/flight';

// Mutable reference so individual tests can control what the autocomplete returns.
// Default: Origin -> JFK, Destination -> LAX (different airports).
// Tests that need same-airport scenario set this to true.
let forceSameAirport = false;

vi.mock('../AirportAutocomplete', () => ({
  AirportAutocomplete: ({
    label,
    onChange,
    value,
  }: {
    label: string;
    onChange: (a: AirportResult | null) => void;
    value: AirportResult | null;
  }) => (
    <button
      type="button"
      data-testid={`airport-${label.toLowerCase()}`}
      onClick={() => {
        const isOrigin = label === 'Origin';
        const iata = forceSameAirport ? 'JFK' : isOrigin ? 'JFK' : 'LAX';
        const city = forceSameAirport ? 'New York' : isOrigin ? 'New York' : 'Los Angeles';
        onChange({
          iata_code: iata,
          name: `${label} Airport`,
          city,
          country: 'US',
        });
      }}
    >
      {value ? value.iata_code : `Select ${label}`}
    </button>
  ),
}));

const FUTURE_FROM = '2099-04-01';
const FUTURE_TO = '2099-04-10';
const PAST_DATE = '2020-01-01';
const PAST_DATE_TO = '2020-01-10';
// Date range > 30 days
const RANGE_OVER_30_TO = '2099-05-15';

function fillValidOneWayForm() {
  fireEvent.click(screen.getByTestId('airport-origin'));
  fireEvent.click(screen.getByTestId('airport-destination'));
  fireEvent.change(screen.getByLabelText('Departure from'), {
    target: { value: FUTURE_FROM },
  });
  fireEvent.change(screen.getByLabelText('Departure to'), {
    target: { value: FUTURE_TO },
  });
}

describe('SearchForm', () => {
  beforeEach(() => {
    forceSameAirport = false;
  });

  it('one-way search submits correctly', () => {
    const onSearch = vi.fn();
    render(<SearchForm onSearch={onSearch} isLoading={false} />);

    fillValidOneWayForm();

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    expect(onSearch).toHaveBeenCalledTimes(1);
    const params: SearchParams = onSearch.mock.calls[0][0];
    expect(params.origin).toEqual({
      iata_code: 'JFK',
      name: 'Origin Airport',
      city: 'New York',
      country: 'US',
    });
    expect(params.destination).toEqual({
      iata_code: 'LAX',
      name: 'Destination Airport',
      city: 'Los Angeles',
      country: 'US',
    });
    expect(params.trip_type).toBe('one_way');
    expect(params.departure_date_from).toBe(FUTURE_FROM);
    expect(params.departure_date_to).toBe(FUTURE_TO);
    expect(params.adults).toBe(1);
    expect(params.max_stops).toBeNull();
  });

  it('return date fields are hidden for one_way', () => {
    const { container } = render(<SearchForm onSearch={vi.fn()} isLoading={false} />);
    // Elements are always in the DOM; hidden via 'invisible' class (visibility: hidden)
    expect(container.querySelector('.invisible')).toBeInTheDocument();
    // The return-from input should be in the DOM but inside the invisible container
    expect(screen.getByLabelText('Return from')).toBeInTheDocument();
  });

  it('return date fields are visible for round_trip', () => {
    render(<SearchForm onSearch={vi.fn()} isLoading={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Round Trip' }));
    expect(screen.getByLabelText('Return from')).toBeInTheDocument();
    expect(screen.getByLabelText('Return to')).toBeInTheDocument();
  });

  it('Search button is disabled when isLoading=true', () => {
    render(<SearchForm onSearch={vi.fn()} isLoading={true} />);
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled();
  });

  it('date range > 30 days shows error, onSearch NOT called', () => {
    const onSearch = vi.fn();
    render(<SearchForm onSearch={onSearch} isLoading={false} />);

    fireEvent.click(screen.getByTestId('airport-origin'));
    fireEvent.click(screen.getByTestId('airport-destination'));
    fireEvent.change(screen.getByLabelText('Departure from'), {
      target: { value: FUTURE_FROM },
    });
    fireEvent.change(screen.getByLabelText('Departure to'), {
      target: { value: RANGE_OVER_30_TO },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    expect(screen.getByRole('alert')).toHaveTextContent(/30 days/i);
    expect(onSearch).not.toHaveBeenCalled();
  });

  it('past departure date shows error, onSearch NOT called', () => {
    const onSearch = vi.fn();
    render(<SearchForm onSearch={onSearch} isLoading={false} />);

    fireEvent.click(screen.getByTestId('airport-origin'));
    fireEvent.click(screen.getByTestId('airport-destination'));
    fireEvent.change(screen.getByLabelText('Departure from'), {
      target: { value: PAST_DATE },
    });
    fireEvent.change(screen.getByLabelText('Departure to'), {
      target: { value: PAST_DATE_TO },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    expect(screen.getByRole('alert')).toHaveTextContent(/past/i);
    expect(onSearch).not.toHaveBeenCalled();
  });

  it('same origin and destination shows error, onSearch NOT called', () => {
    forceSameAirport = true;
    const onSearch = vi.fn();
    render(<SearchForm onSearch={onSearch} isLoading={false} />);

    fireEvent.click(screen.getByTestId('airport-origin'));
    fireEvent.click(screen.getByTestId('airport-destination'));
    fireEvent.change(screen.getByLabelText('Departure from'), {
      target: { value: FUTURE_FROM },
    });
    fireEvent.change(screen.getByLabelText('Departure to'), {
      target: { value: FUTURE_TO },
    });

    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    expect(screen.getByRole('alert')).toHaveTextContent(/same/i);
    expect(onSearch).not.toHaveBeenCalled();
  });
});
