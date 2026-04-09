# Design: m03 — UX Overhaul

## Verification Plan

| Pattern | Risk Category | Tier | Action | Justification |
|---------|--------------|------|--------|---------------|
| Tailwind CSS v3 + PostCSS + Vite 5 build | R5 | Smoke | SKIP (done) | v001 — verified in POC, VIABLE |
| shadcn/ui CLI non-interactive init in Vite | R5 | Full POC | SKIP (done) | v002 — verified in POC, VIABLE with constraints |
| Vitest jsdom + Tailwind CSS + shadcn/ui imports | R2 | Smoke | SKIP (done) | v003 — verified in POC, VIABLE |
| Lucide React icon imports | R1 | — | SKIP | Stdlib-trivial: `import { Icon } from 'lucide-react'`; well-documented; auto-installed by shadcn |
| React state + Tailwind class conditionals | R1 | — | SKIP | Standard React pattern; no new integration boundary |
| Recharts axis/tooltip style props | R1 | — | SKIP | Recharts already used in m02 (PriceHistoryChart); only changing inline style props |

All three technology questions were POC'd before design. Results:
- **v001**: Tailwind CSS v3 + Vite 5 via PostCSS — VIABLE. See `poc/tailwind-vite-integration.md`
- **v002**: shadcn/ui non-interactive init — VIABLE with constraints (Nova CSS incompatible with v3; manual index.css required). See `poc/shadcn-noninteractive.md`
- **v003**: Vitest + Tailwind + shadcn — VIABLE, no config changes needed. See `poc/vitest-css-compat.md`

---

## Architecture Overview

This milestone is a **pure frontend styling pass** — no backend changes, no new routes, no new API calls, no new TypeScript types. Every existing component file is updated in-place with Tailwind utility classes and shadcn/ui primitive components.

**Tech additions:**
- `tailwindcss@3`, `postcss`, `autoprefixer` (devDependencies)
- `radix-ui`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge` (dependencies, installed by shadcn)
- shadcn/ui components in `src/components/ui/` (button, card, badge, dialog, input, label, select, skeleton, separator, tooltip, alert-dialog)
- `@fontsource/inter` (dependency) — Inter font via npm, no CDN dependency

**Test compatibility:** All 98 existing tests continue to pass. The `window.confirm` test in `TrackedSearchRow.test.tsx` must be updated when `TrackedSearchRow` switches to `AlertDialog` (the test currently mocks `window.confirm` — this mock must be removed and replaced with a click on the shadcn AlertDialog confirm button).

**UX Review Warnings addressed:**
1. Track button elevation — moved to a dedicated sticky row below results header, not inline with toggle buttons
2. PriceGrid color legend — added inline legend row above the grid table
3. Return date layout shift — rendered with `visibility: hidden` / `opacity-0` when One Way is selected, preserving vertical space; One Way is the default

---

## Data Flow

No data flow changes. Components receive the same props. The visual layer is additive: existing props, state, and API calls are untouched. The only behavioral change is replacing `window.confirm()` in `TrackedSearchRow` with a shadcn `AlertDialog` — this requires adding `useState<boolean>` for the dialog open state inside `TrackedSearchRow`.

---

## Component Details

### Setup Layer (`t01` — Tooling & Config)

**Files created/modified:**
- `frontend/package.json` — install tailwindcss@3, postcss, autoprefixer, @fontsource/inter
- `frontend/tailwind.config.ts` — content glob, CSS variable color mappings, brand color extensions, Inter font family
- `frontend/postcss.config.js` — tailwindcss + autoprefixer plugins
- `frontend/tsconfig.json` — add `baseUrl: "."` and `paths: { "@/*": ["./src/*"] }`
- `frontend/vite.config.ts` — add `resolve.alias: { '@': path.resolve(__dirname, './src') }`
- `frontend/src/index.css` — @tailwind directives + HSL CSS variable definitions
- `frontend/src/main.tsx` — add `import './index.css'` and `import '@fontsource/inter/400.css'` / `import '@fontsource/inter/600.css'`
- `frontend/src/components/ui/` — shadcn components (installed via CLI, NOT hand-written)
- `frontend/src/lib/utils.ts` — `cn()` utility (installed by shadcn CLI)
- `frontend/components.json` — shadcn config file

**shadcn CLI commands (run in sequence during task):**
```bash
npx shadcn@latest init --template=vite --yes --base=radix --preset=nova
npx shadcn@latest add card badge dialog input label select skeleton separator tooltip alert-dialog --yes
```
The button component is installed by `init`. After running the CLI, replace the generated `src/index.css` with the v3-compatible version and update `tailwind.config.ts` with color/font config.

**tailwind.config.ts final shape:**
```ts
import type { Config } from 'tailwindcss';
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: { 50: '#f0f9ff', 500: '#0284c7', 600: '#0284c7', 700: '#0369a1' },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
} satisfies Config;
```

**src/index.css final shape (v3-compatible, HSL variables):**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 210 40% 98%;    /* sky-50 equivalent */
    --foreground: 222 84% 5%;     /* neutral-900 */
    --card: 0 0% 100%;
    --card-foreground: 222 84% 5%;
    --popover: 0 0% 100%;
    --popover-foreground: 222 84% 5%;
    --primary: 199 89% 48%;       /* sky-500 */
    --primary-foreground: 0 0% 100%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222 84% 5%;
    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;
    --accent: 210 40% 96%;
    --accent-foreground: 222 84% 5%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --border: 214 32% 91%;
    --input: 214 32% 91%;
    --ring: 199 89% 48%;
    --radius: 0.5rem;
  }
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground font-sans;
  }
}
```

### App Shell & NavBar (`t02`)

**`frontend/src/App.tsx`** — Wrap layout:
```tsx
<div className="min-h-screen bg-sky-50 font-sans">
  <NavBar />
  <main className="max-w-5xl mx-auto px-4 py-8">
    <Routes ... />
  </main>
</div>
```
Remove the bare `<BrowserRouter><NavBar /><Routes>` structure and wrap with the layout div. The `<main>` wrapper moves from `HomePage` and `TrackedSearchesPage` into `App.tsx`.

**`frontend/src/components/NavBar/index.tsx`:**
- Fixed top bar: `fixed top-0 left-0 right-0 z-50 h-14 bg-white border-b border-neutral-200 shadow-sm`
- Inner: `max-w-5xl mx-auto px-4 h-full flex items-center justify-between`
- Brand: `<Plane>` icon + "FlightTracker" text in `font-bold text-sky-600`
- Nav links use `useLocation()` to determine active route — active link gets `text-sky-600 font-medium border-b-2 border-sky-600`, inactive gets `text-neutral-600 hover:text-sky-600`
- `App.tsx` `<main>` must add `pt-14` to clear the fixed NavBar height

**Key constraint:** The `NavBar` currently does not use `useLocation`, so it must import `useLocation` from `react-router-dom`.

### SearchForm (`t03`)

**`frontend/src/components/SearchForm/index.tsx`** — Keep all existing state and validation logic verbatim. Only change the JSX return value.

**Structure:**
```
<Card>
  <CardHeader><CardTitle>Find Flights</CardTitle></CardHeader>
  <CardContent>
    <form>
      {/* Trip type pill toggle */}
      {/* Airport row — 2-col grid md+ */}
      {/* Departure date row — 2-col */}
      {/* Return date row — always rendered, visibility-hidden when one_way */}
      {/* Adults + Max Stops row — 2-col */}
      {/* Error alert */}
      {/* Search button */}
    </form>
  </CardContent>
</Card>
```

**Trip type toggle:** Two `<button>` elements side by side with `rounded-full` pill style. Active: `bg-sky-600 text-white`. Inactive: `bg-white text-neutral-700 border border-neutral-300`. Existing `aria-pressed` attributes preserved.

**Airport row:** `<div className="grid grid-cols-1 md:grid-cols-2 gap-4">` wrapping two `<AirportAutocomplete>` fields.

**Return date row (UX Warning #3 — layout shift fix):**
```tsx
<div className={`grid grid-cols-2 gap-4 transition-all duration-200 ${
  tripType === 'one_way' ? 'invisible opacity-0 pointer-events-none' : 'visible opacity-100'
}`}>
  {/* Return from date input */}
  {/* Return to date input */}
</div>
```
This preserves vertical space when hidden, preventing layout shift. The fields remain in the DOM but are non-interactive when `one_way`.

**Search button:** `<button className="w-full h-12 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors">`. When `isLoading`: show `<Loader2 className="h-4 w-4 animate-spin" />` before text. The `disabled` attribute is already present in existing code.

**Test compatibility:** Tests use `getByLabelText('Return from')` and `getByLabelText('Return to')`. With the visibility approach (elements remain in DOM), `getByLabelText` still finds them — no test changes needed. The test `'return date fields are hidden for one_way'` checks `queryByLabelText('Return from') → not.toBeInTheDocument()`. Since we now keep these elements in the DOM (but invisible), this test WILL FAIL. The test must be updated to check for `visibility: hidden` or `aria-hidden` instead. Document this expected test update in the task.

**`frontend/src/components/AirportAutocomplete/index.tsx`** (also in t03):
- Input: add `PlaneTakeoff`/`PlaneLanding` icon prefix (distinguish by `label` prop) in a relative wrapper
- Dropdown: `absolute z-50 w-full mt-1 bg-white shadow-lg border border-neutral-200 rounded-lg overflow-hidden`
- Each suggestion: `px-3 py-2 cursor-pointer hover:bg-sky-50`
- IATA code: `font-mono font-bold text-sky-700`
- Airport name: `text-sm text-neutral-500`

### ResultsList, FlightCard & TrackButton (`t04`)

**`frontend/src/pages/HomePage.tsx`** — Structural change: move TrackButton out of the results header into a dedicated sticky bar.

Track button placement (UX Warning #1):
```tsx
{status === 'success' && results.length > 0 && (
  <div className="sticky bottom-0 bg-white border-t border-neutral-200 py-3 px-4 flex justify-end shadow-lg">
    <TrackButton searchParams={searchParams!} currency={results[0]?.currency ?? 'USD'} />
  </div>
)}
```
The List/Grid toggles stay in the ResultsList header row.

**`frontend/src/components/ResultsList/index.tsx`:**
- Loading state: replace text with 3 `<Skeleton>` card placeholders (each ~80px tall, full-width, `rounded-lg mb-4`)
- Results header row: `flex items-center justify-between mb-4`. Left: "X flights found" in `text-sm text-neutral-500`. Right: `LayoutList` / `LayoutGrid` icon buttons.
- Move view toggle buttons INTO ResultsList (accept `viewMode` and `onViewModeChange` props). Update `HomePage` to pass them.

**`frontend/src/components/ResultsList/FlightCard.tsx`:**
- Wrap in shadcn `<Card className="hover:shadow-md transition-shadow mb-4">`
- Price: `<span className="text-2xl font-bold text-sky-600">{offer.price}</span>`
- Header row: price right-aligned (`ml-auto`)
- Departure/return dates: `text-sm text-neutral-500`
- `<SegmentRow>`: airport codes `text-xl font-semibold`, times `text-base`, duration+stops `text-sm text-neutral-500`
- Stops badge: `<Badge variant="secondary" className="bg-green-100 text-green-700">Nonstop</Badge>` or `<Badge className="bg-amber-100 text-amber-700">X stops</Badge>`
- `<Separator className="my-2" />` between outbound and return sections
- Add `aria-hidden="true"` to skeleton elements

**`frontend/src/components/TrackButton/index.tsx`:**
- Trigger button: `<Button variant="outline" className="gap-2"><Bell className="h-4 w-4" />Track this search</Button>`
- Tracking state: `<Button disabled className="gap-2 text-neutral-400"><BellRing className="h-4 w-4" />Tracking</Button>`
- Replace `<div role="dialog">` with shadcn `<Dialog>` / `<DialogContent>`
- Route summary in `<DialogHeader>`: `{origin} → {destination}` + trip type badge
- Summary section: `bg-sky-50 rounded-lg p-3 text-sm`
- Email field: `<Input type="email" />` with label
- Threshold field: `<Input type="number" />` with label
- Validation errors: `<p className="text-sm text-red-500 mt-1">`
- Actions: `<Button className="w-full bg-sky-600">Save</Button>` + `<Button variant="ghost">Cancel</Button>`
- `DialogContent` already provides backdrop and Escape-key-close via shadcn

**Test compatibility:** The TrackButton tests check `getByRole('dialog')`. shadcn's `Dialog` renders `role="dialog"` on `DialogContent` — this is preserved. The `queryByRole('dialog')` → `not.toBeInTheDocument()` check when modal is closed: shadcn Dialog uses a `DialogPortal` which removes from DOM when closed — this should work. However, if the Dialog uses a portal that mounts outside the test render container, `screen.getByRole('dialog')` may fail. This must be confirmed when implementing. If shadcn's Dialog portal causes issues in jsdom, use `open` prop with conditional rendering instead of the default portal behavior.

### PriceGrid (`t05`)

**`frontend/src/components/PriceGrid/index.tsx`:**

Replace the existing `priceColor()` HSL function (which returns raw `hsl()` strings) with a `priceTier()` function returning Tailwind class names based on percentile:
```ts
function priceTier(price: number, p25: number, p75: number): string {
  if (price <= p25) return 'bg-green-50 text-green-700';
  if (price >= p75) return 'bg-red-50 text-red-600';
  return 'bg-white text-neutral-900';
}
```
Where `p25` = 25th percentile price and `p75` = 75th percentile price.

**Color legend (UX Warning #2):** Add an inline legend row above the table:
```tsx
<div className="flex gap-3 text-xs mb-2 text-neutral-600">
  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-green-50 border border-green-200 inline-block"></span>Lowest prices</span>
  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-white border border-neutral-200 inline-block"></span>Mid-range</span>
  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm bg-red-50 border border-red-200 inline-block"></span>Highest prices</span>
</div>
```

**Table styling:**
- Outer: `overflow-x-auto` wrapper for horizontal scroll on narrow viewports
- Table: `border-collapse w-full text-sm`
- Header row/column: `bg-neutral-50 text-neutral-500 text-xs font-semibold p-2`
- Data cells: `p-2 font-medium text-center cursor-pointer hover:ring-2 hover:ring-sky-400 hover:ring-inset transition-all` + tier class
- Empty cells: `bg-neutral-50`

**Note:** The `priceColor` function is exported and tested in `PriceGrid.test.tsx`. Rename the export to `priceTier` and update the test to match the new string return values. Document this as an expected test update in the task.

### TrackedSearchesPage & TrackedSearchRow (`t06`)

**`frontend/src/pages/TrackedSearchesPage.tsx`:**
- Loading state: `<p className="text-center py-12 text-neutral-500">Loading...</p>`
- Error state: `<p role="alert" className="text-red-500">...</p>`
- Empty state (replace simple `<p>`):
  ```tsx
  <div className="flex flex-col items-center py-16 text-center gap-4">
    <Search className="h-16 w-16 text-neutral-300" />
    <h2 className="text-xl font-semibold text-neutral-700">No tracked searches yet</h2>
    <p className="text-neutral-500">Search for a flight and click "Track this search" to get started</p>
    <Button asChild variant="outline"><Link to="/">Search flights</Link></Button>
  </div>
  ```
- Page header: `<h1 className="text-2xl font-bold mb-1">My Tracked Searches</h1><p className="text-neutral-500 text-sm mb-6">Prices checked automatically every hour</p>`
- Remove the inline `<main>` wrapper (moved to App.tsx)

**`frontend/src/components/TrackedSearchRow/index.tsx`:**

**AlertDialog for delete (replaces `window.confirm`):**
Add state: `const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);`
```tsx
<AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
  <AlertDialogTrigger asChild>
    <Button variant="outline" size="sm" className="text-red-600 border-red-300 hover:bg-red-50">Delete</Button>
  </AlertDialogTrigger>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Delete tracked search?</AlertDialogTitle>
      <AlertDialogDescription>This will remove {search.origin} → {search.destination} from your tracked searches.</AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction onClick={handleConfirmDelete} className="bg-red-600 hover:bg-red-700">Delete</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```
Rename `handleDelete` → `handleConfirmDelete` (remove `window.confirm` call, just execute the delete).

**Card layout:**
```
<Card className="mb-4 p-4">
  <div className="flex items-start justify-between">
    <div>
      <div className="flex items-center gap-2">
        <span className="text-xl font-semibold">{origin} → {destination}</span>
        <Badge variant="secondary">{trip_type}</Badge>
        {bestBelowThreshold && <TrendingDown className="h-4 w-4 text-green-600" />}
      </div>
      <div className="text-sm text-neutral-500 mt-1">
        Dep: {departure_date_from} – {departure_date_to}
        {/* return dates if round trip */}
      </div>
      <div className="flex gap-4 mt-2">
        <span>Alert: <span className="font-medium">${threshold_price}</span></span>
        <span data-testid="best-price">Best: <span className={bestBelowThreshold ? 'text-green-600 font-bold' : 'font-medium'}>{current_best_price ?? '–'}</span></span>
        <span data-testid="last-checked" className="text-neutral-400 text-xs">Last checked: {relativeTime}</span>
      </div>
    </div>
    <div className="flex gap-2">
      <Button variant="outline" size="sm" aria-expanded={expanded} onClick={handleToggleHistory}>
        History {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </Button>
      {/* AlertDialog delete button */}
    </div>
  </div>
  {/* Expandable history section */}
  {expanded && (
    <div className="mt-4 border-t border-neutral-200 pt-4">
      ...
    </div>
  )}
</Card>
```

**Relative time** with `Intl.RelativeTimeFormat`:
```ts
function relativeTime(isoString: string | null): string {
  if (!isoString) return 'Never';
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffHours = Math.round(diffMs / 3600000);
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}
```

**PriceHistoryChart styling** (update `frontend/src/components/PriceHistoryChart/index.tsx`):
- `<Line stroke="#0284c7" strokeWidth={2} dot={{ fill: '#0284c7' }} />`
- `<XAxis tick={{ fontSize: 11, fill: '#64748b' }} />`
- `<YAxis tick={{ fontSize: 11, fill: '#64748b' }} />`
- `<CartesianGrid stroke="#e2e8f0" />`
- `<Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0' }} />`
- Change height from 300 to 200 as per PRD

**Test compatibility:** `TrackedSearchRow.test.tsx` currently mocks `window.confirm` and tests that `window.confirm` was called with the correct message. These tests will break when `window.confirm` is removed. The updated tests must:
1. Remove `vi.spyOn(window, 'confirm').mockReturnValue(true/false)` 
2. Click the Delete button to open the AlertDialog
3. Click the `AlertDialogAction` button to confirm
4. Verify `deleteTrackedSearch` was called
The test that checks "does not call deleteTrackedSearch when confirm is cancelled" must click `AlertDialogCancel` instead.

---

## Error Handling

All error states already handled in existing logic. Visual changes only:
- Form validation error: `<p role="alert" className="text-sm text-red-500 mt-2">` (preserves role="alert" for tests)
- Search error: `<div role="alert" className="text-red-500 p-4 bg-red-50 rounded-lg">`
- API errors in TrackButton/TrackedSearchRow: `<p role="alert" className="text-sm text-red-500">`
- Delete errors: `<span role="alert" className="text-sm text-red-500">` (must preserve data-testid and role="alert" for tests)

---

## Development Server

```bash
cd frontend && npm run dev
```
Vite dev server with HMR at http://localhost:5173 (proxies /api to http://localhost:8000).

---

## ADR References

- **ADR-004** (Vite Dev Proxy): No change. `server.proxy` config preserved in `vite.config.ts` when adding `resolve.alias`.
- **ADR-007** (BrowserRouter): No change. Routing structure is preserved. NavBar now uses `useLocation()` for active-link detection (compatible with BrowserRouter).
- **New ADR-008**: CSS architecture decision (Tailwind v3 via PostCSS, not v4 via Vite plugin) — see ADR section below.
