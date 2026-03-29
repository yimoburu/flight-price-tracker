import { useState, useEffect } from 'react';
import type { AirportResult } from '../../types/flight';
import { searchAirports } from '../../api/airports';

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
    <div>
      <label htmlFor={id}>{label}</label>
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
      />
      {loading && <span>Searching...</span>}
      {error && <span role="alert">{error}</span>}
      {isOpen && suggestions.length > 0 && (
        <ul id={listboxId} role="listbox">
          {suggestions.map((airport) => (
            <li
              key={airport.iata_code}
              role="option"
              aria-selected={false}
              onMouseDown={() => handleSelect(airport)}
            >
              <div>{airport.iata_code} — {airport.city}, {airport.country}</div>
              <div style={{ fontSize: '0.85em' }}>{airport.name}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
