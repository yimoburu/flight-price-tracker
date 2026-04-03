# Research: React/TypeScript Frontend Patterns

Source: https://vitejs.dev/guide/
Source: https://react.dev/reference/react
Source: https://fastapi.tiangolo.com/tutorial/cors/

## Vite + React + TypeScript Setup

Standard Vite project created via:
```
npm create vite@latest frontend -- --template react-ts
```

Generates: `vite.config.ts`, `tsconfig.json` (strict mode), `src/` structure.

## API Proxy for Development (Vite)

Avoid CORS issues in development by proxying `/api` to the FastAPI backend:

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

This means all `/api/v1/*` calls from the frontend go to FastAPI directly without CORS.

## Debounced Airport Autocomplete

Use `useCallback` + `setTimeout` for debouncing:

```typescript
const [query, setQuery] = useState('');
const [suggestions, setSuggestions] = useState<Airport[]>([]);

useEffect(() => {
  if (query.length < 3) { setSuggestions([]); return; }
  const timer = setTimeout(async () => {
    const results = await searchAirports(query);
    setSuggestions(results);
  }, 300);
  return () => clearTimeout(timer);
}, [query]);
```

## Price Grid Color Coding

For round-trip 2D grid, color cells from green (cheapest) to red (most expensive)
using CSS `hsl()` interpolation:

```typescript
function priceColor(price: number, min: number, max: number): string {
  const ratio = (price - min) / (max - min); // 0 = cheapest, 1 = most expensive
  const hue = Math.round(120 - ratio * 120); // 120 = green, 0 = red
  return `hsl(${hue}, 70%, 45%)`;
}
```

## Form Validation Pattern

Frontend validation before submitting:
- Date range max 30 days enforced via `dayjs` or `date-fns`
- Departure date not in past
- Origin != Destination
- Return date range required and valid for round trips

## Fetch with Abort Controller

For airport autocomplete (cancel previous request on new keystroke):

```typescript
useEffect(() => {
  const controller = new AbortController();
  fetch(`/api/v1/airports?q=${query}`, { signal: controller.signal })
    .then(r => r.json())
    .then(setSuggestions)
    .catch(e => { if (e.name !== 'AbortError') setError(e.message); });
  return () => controller.abort();
}, [query]);
```

## Key Dependencies

- `axios` or native `fetch` for HTTP
- `date-fns` for date math (range validation, formatting)
- React 18 strict mode enabled in dev
- `@types/react`, `@types/react-dom` for TypeScript support
