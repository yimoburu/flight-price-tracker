import { useState, useEffect } from 'react';
import type { AirportResult } from '../../types/flight';
import { searchAirports } from '../../api/airports';
import { PlaneTakeoff, PlaneLanding } from 'lucide-react';

interface AirportAutocompleteProps {
  label: string;
  value: AirportResult | null;
  onChange: (airport: AirportResult | null) => void;
  placeholder?: string;
  id: string;
  disabled?: boolean;
}

export function AirportAutocomplete({
  label,
  value,
  onChange,
  placeholder,
  id,
  disabled,
}: AirportAutocompleteProps): JSX.Element {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<AirportResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const listboxId = `${id}-listbox`;

  const displayValue = value ? `${value.iata_code} — ${value.city}` : query;

  useEffect(() => {
    if (query.length < 3) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }
    const timer = setTimeout(() => {
      setLoading(true);
      setError('');
      searchAirports(query)
        .then((results) => {
          setSuggestions(results.slice(0, 10));
          setIsOpen(true);
        })
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange(null);
    setQuery(e.target.value);
  }

  function handleSelect(airport: AirportResult) {
    onChange(airport);
    setQuery('');
    setIsOpen(false);
    setSuggestions([]);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  }

  function handleBlur() {
    setTimeout(() => setIsOpen(false), 150);
  }

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-neutral-700">{label}</label>
      <div className="relative">
        <div className="relative flex items-center">
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 pointer-events-none">
            {label === 'Origin' ? <PlaneTakeoff className="h-4 w-4" /> : <PlaneLanding className="h-4 w-4" />}
          </div>
          <input
            id={id}
            type="text"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={isOpen}
            aria-controls={listboxId}
            value={displayValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            placeholder={placeholder}
            disabled={disabled}
            autoComplete="off"
            className="w-full pl-9 pr-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-sky-400"
          />
        </div>
        {loading && <span>Searching...</span>}
        {error && <span role="alert">{error}</span>}
        {isOpen && suggestions.length > 0 && (
          <ul id={listboxId} role="listbox"
            className="absolute z-50 w-full mt-1 bg-white shadow-lg border border-neutral-200 rounded-lg overflow-hidden max-h-64 overflow-y-auto">
            {suggestions.map((airport) => (
              <li
                key={airport.iata_code}
                role="option"
                aria-selected={false}
                onMouseDown={() => handleSelect(airport)}
                className="px-3 py-2 cursor-pointer hover:bg-sky-50 flex flex-col"
              >
                <div>
                  <span className="font-mono font-bold text-sky-700">{airport.iata_code}</span>
                  {` — ${airport.city}, ${airport.country}`}
                </div>
                <span className="text-sm text-neutral-500">{airport.name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
