import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AirportAutocomplete } from './index';
import * as airportsApi from '../../api/airports';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

vi.mock('../../api/airports');

const mockAirports = [
  { iata_code: 'LHR', name: 'Heathrow', city: 'London', country: 'GB' },
  { iata_code: 'LGW', name: 'Gatwick', city: 'London', country: 'GB' },
];

describe('AirportAutocomplete', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(airportsApi.searchAirports).mockResolvedValue(mockAirports);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('renders label and input', () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    expect(screen.getByLabelText('Origin')).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('input has role="combobox", aria-autocomplete="list", aria-expanded="false" initially', () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    expect(input).toHaveAttribute('aria-autocomplete', 'list');
    expect(input).toHaveAttribute('aria-expanded', 'false');
  });

  it('typing 3+ chars triggers searchAirports after 300ms debounce and shows dropdown', async () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LON' } });

    // Before debounce fires, searchAirports should not be called
    expect(airportsApi.searchAirports).not.toHaveBeenCalled();

    // Advance timers by 300ms
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    // After debounce, searchAirports should be called with the query
    expect(airportsApi.searchAirports).toHaveBeenCalledWith('LON');

    // Wait for state updates (promise resolution)
    await waitFor(() => {
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent('LHR');
    expect(options[1]).toHaveTextContent('LGW');
  });

  it('typing fewer than 3 chars does NOT call searchAirports', async () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LO' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(airportsApi.searchAirports).not.toHaveBeenCalled();
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('selecting an item calls onChange with AirportResult and closes dropdown', async () => {
    const handleChange = vi.fn();
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={handleChange}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LON' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    await waitFor(() => {
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    const lhrOption = screen.getAllByRole('option')[0];
    fireEvent.mouseDown(lhrOption);

    expect(handleChange).toHaveBeenCalledWith(mockAirports[0]);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('Escape key closes dropdown without selecting', async () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LON' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    await waitFor(() => {
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('aria-expanded is true when dropdown is open, false when closed', async () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    expect(input).toHaveAttribute('aria-expanded', 'false');

    fireEvent.change(input, { target: { value: 'LON' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    await waitFor(() => {
      expect(input).toHaveAttribute('aria-expanded', 'true');
    });

    fireEvent.keyDown(input, { key: 'Escape' });
    expect(input).toHaveAttribute('aria-expanded', 'false');
  });

  it('disabled prop sets input disabled attribute', () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
        disabled={true}
      />
    );
    expect(screen.getByRole('combobox')).toBeDisabled();
  });

  it('shows selected airport as "IATA — city" when value is set', () => {
    const selectedAirport = mockAirports[0];
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={selectedAirport}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox') as HTMLInputElement;
    expect(input.value).toBe('LHR — London');
  });

  it('shows loading text while fetching', async () => {
    // Make searchAirports take time by not resolving immediately
    let resolveSearch!: (val: typeof mockAirports) => void;
    vi.mocked(airportsApi.searchAirports).mockReturnValue(
      new Promise((resolve) => { resolveSearch = resolve; })
    );

    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LON' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(screen.getByText('Searching...')).toBeInTheDocument();

    // Resolve to clean up
    await act(async () => {
      resolveSearch(mockAirports);
    });
  });

  it('shows error message when searchAirports rejects', async () => {
    vi.mocked(airportsApi.searchAirports).mockRejectedValue(new Error('Network error'));

    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LON' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Network error');
    });
  });

  it('dropdown items show IATA, city, country and airport name', async () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
      />
    );
    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'LON' } });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    await waitFor(() => {
      expect(screen.getByRole('listbox')).toBeInTheDocument();
    });

    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveTextContent('LHR — London, GB');
    expect(options[0]).toHaveTextContent('Heathrow');
  });

  it('placeholder prop is passed through to input', () => {
    render(
      <AirportAutocomplete
        label="Origin"
        id="origin"
        value={null}
        onChange={vi.fn()}
        placeholder="Search airport or city"
      />
    );
    expect(screen.getByPlaceholderText('Search airport or city')).toBeInTheDocument();
  });
});
