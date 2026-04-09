# PRD: m03 — UX Overhaul

## 1. Milestone Overview

The existing app (m01 + m02) is fully functional but has **zero visual styling** — every component renders as unstyled browser-default HTML with no CSS, no layout, no color, no typography, and no visual hierarchy. This milestone transforms the UI into a polished, modern, state-of-the-art travel-search experience on par with Google Flights and Kayak.

No backend changes. No new features. This milestone is purely a frontend visual and experience overhaul.

**Design philosophy:** Clean, spacious, information-dense where it matters. Travelers scan for price and route quickly; the UI must make those jump out. Everything else is secondary.

---

## 2. Technology Additions

| Concern | Technology | Reason |
|---|---|---|
| Utility-first styling | **Tailwind CSS v3** | Standard for modern React; Vite plugin is 2-line config |
| Accessible components | **shadcn/ui** | Pre-built, accessible Radix UI + Tailwind components; avoids reimplementing Dialog, Select, Badge from scratch |
| Icons | **Lucide React** | Consistent icon set; already a shadcn/ui peer dep |
| Animations | **Tailwind CSS transitions** only | No extra dep; keep it light |

shadcn/ui components to install: `Button`, `Card`, `Badge`, `Dialog`, `Input`, `Label`, `Select`, `Skeleton`, `Separator`, `Tooltip`.

No changes to: backend, tests (existing tests must still pass), routing, API layer, or TypeScript types.

---

## 3. Visual Identity

### Color Palette (Tailwind CSS custom tokens via `tailwind.config.ts`)

| Token | Hex | Usage |
|---|---|---|
| `brand-500` | `#0284C7` (sky-600) | Primary actions, active states, links |
| `brand-50` | `#F0F9FF` (sky-50) | Page background |
| `neutral-900` | `#0F172A` | Primary text |
| `neutral-500` | `#64748B` | Secondary/muted text |
| `neutral-200` | `#E2E8F0` | Borders, dividers |
| `success-500` | `#16A34A` | Price drop indicator |
| `warning-500` | `#D97706` | Threshold warning |
| `error-500` | `#DC2626` | Error states |

### Typography
- Font: **Inter** (Google Fonts CDN import in `index.html`)
- Body: 14px / 1.5 line-height
- Headings: `font-semibold` weight, tracked tighter
- Prices: `font-bold text-2xl` in brand color

### Spacing
- Page max-width: `max-w-5xl mx-auto px-4`
- Card padding: `p-6`
- Section gap: `gap-6`

---

## 4. Component-by-Component Redesign

### 4.1 Layout Shell (`App.tsx`)

Wrap the app in a full-height layout:

```
<div class="min-h-screen bg-sky-50 font-inter">
  <NavBar />
  <main class="max-w-5xl mx-auto px-4 py-8">
    <Routes ... />
  </main>
</div>
```

### 4.2 NavBar

**Current:** Two raw `<Link>` elements inside a `<nav>`, no styling.

**Redesign:**
- Fixed top bar with white background, 1px bottom border, subtle shadow (`shadow-sm`)
- Left: Brand logo — airplane icon (`Plane` from Lucide) + "FlightTracker" in `font-bold text-sky-600`
- Right: Nav links as pill-style buttons; active route underlined or highlighted
- Height: 56px
- Responsive: same layout at 768px+; no hamburger menu required

Acceptance: NavBar visible on both pages, brand name matches above, active route visually distinct.

### 4.3 SearchForm

**Current:** Vertical stack of unstyled inputs and divs with no grouping or spacing.

**Redesign:**

1. **Card container**: wrap entire form in a shadcn `<Card>` with `<CardHeader>` and `<CardContent>`
2. **Trip type toggle**: replace two `<button aria-pressed>` with a styled pill-toggle group (two rounded buttons that look like tabs; active one has `bg-sky-600 text-white`, inactive has `bg-white text-neutral-700 border`)
3. **Airport row**: Origin + Destination side-by-side (2-col grid on ≥768px), each with a search icon in the input prefix area
4. **Date range rows**: "Departure window" label above two date inputs (`From` / `To`) displayed side-by-side
5. **Return date row**: same layout, only visible for round-trip, animates in with `transition-all`
6. **Adults + Max Stops**: inline row, shadcn `<Select>` styled components
7. **Search button**: full-width, `bg-sky-600 hover:bg-sky-700 text-white`, large (`h-12`), with a `Loader2` spinner icon while loading

Layout: form uses CSS Grid (`grid grid-cols-1 gap-4 md:grid-cols-2`) for the field groups.

Acceptance: Form fields are visually grouped, date pair side-by-side, Search button prominent, loading state shows spinner.

### 4.4 AirportAutocomplete

**Current:** Renders a raw `<input>` + label, no dropdown styling.

**Redesign:**
- Input has `PlaneTakeoff` / `PlaneLanding` Lucide icon prefix
- Dropdown suggestions render as a floating `<div>` with `shadow-lg border rounded-lg bg-white` positioned below the input
- Each suggestion row: IATA code in `font-mono font-bold text-sky-700` + city/airport name in muted text
- Highlighted row: `bg-sky-50`
- "No results" state shows muted text placeholder

Acceptance: Dropdown is visually distinct from page content, IATA code stands out.

### 4.5 ResultsList & FlightCard

**Current:** A `<ul>` of `<li>` containing unstyled `<article>` elements.

**Redesign — ResultsList:**
- Results header: "X flights found" in `text-sm text-neutral-500` + List/Grid toggle buttons (icon buttons, `LayoutList` and `LayoutGrid` from Lucide) aligned right
- Track button appears inline in the results header area (right side)
- Animate list entry with `animate-in fade-in` (Tailwind animation)

**Redesign — FlightCard:**

Layout (single card):
```
┌─────────────────────────────────────────────────────────┐
│  [Airline logo placeholder] AA 101    NONSTOP   $299    │
│  JFK  10:00 ──────────── LAX  13:15  5h 15m            │
│  [Outbound details row]                                  │
│  ─────────────────────────────────────────────────────  │
│  [Return details if round-trip]                          │
└─────────────────────────────────────────────────────────┘
```

- Price: `text-2xl font-bold text-sky-600`, right-aligned
- Airport codes: `text-xl font-semibold`
- Times: `text-base text-neutral-900`
- Duration + stops: `text-sm text-neutral-500` centered between airports
- Nonstop badge: `<Badge variant="secondary">` in green; "X stops" in amber
- Card: shadcn `<Card>` with `hover:shadow-md transition-shadow`

**Loading skeleton (FlightCard):** Replace "Searching for flights..." text with 3 `<Skeleton>` card placeholders that match the card shape.

Acceptance: Price stands out, airport codes clear, stop count has visual badge, loading shows skeleton cards.

### 4.6 PriceGrid

**Current:** No styling — raw table or div grid.

**Redesign:**
- Table layout with departure date on rows, return date on columns (or just departure dates for one-way)
- Each cell: price in `text-sm font-medium`, background color-coded by price tier:
  - Lowest 25%: `bg-green-50 text-green-700`
  - Middle 50%: `bg-white text-neutral-900`
  - Highest 25%: `bg-red-50 text-red-600`
- Header row/column: `bg-neutral-50 text-neutral-500 text-xs font-semibold`
- Hover: `hover:ring-2 hover:ring-sky-400`
- Scrollable horizontally on narrow viewports

Acceptance: Cheap dates visually green, expensive dates visually red, color scale makes cheapest date immediately obvious.

### 4.7 TrackButton & Track Modal

**Current:** A plain `<button>` that opens a raw `<div role="dialog">` with no backdrop.

**Redesign — Button:**
- `<Button variant="outline">` with `Bell` Lucide icon + "Track this search" text
- When tracking: `<Button disabled>` with `BellRing` icon + "Tracking" in muted color

**Redesign — Modal (shadcn `<Dialog>`):**
- Replace `<div role="dialog">` with shadcn `<Dialog>` / `<DialogContent>`
- Title: "Track this search" with route summary (`JFK → LAX`)
- Summary section: route, trip type badge, date range — styled with `bg-sky-50 rounded-lg p-3`
- Email input: shadcn `<Input type="email">` with `Mail` icon
- Price threshold input: shadcn `<Input type="number">` with currency label
- Validation errors: inline below each field in `text-sm text-red-500`
- Actions: `Save` (primary sky button, full-width) + `Cancel` (ghost)
- Backdrop: shadcn Dialog provides this automatically

Acceptance: Modal has backdrop overlay, clicking outside closes it, validation errors are inline.

### 4.8 TrackedSearchesPage

**Current:** Flat list of unstyled divs with inline text spans.

**Redesign:**

**Page header:**
- `h1` "My Tracked Searches" styled `text-2xl font-bold`
- Subtitle "Prices checked automatically every hour"

**Empty state:**
- Centered illustration: `Search` Lucide icon, large, in `text-neutral-300`
- "No tracked searches yet" heading + "Search for a flight and click 'Track this search' to get started" body text
- CTA button linking to `/`

**Each tracked search: Card layout**
```
┌───────────────────────────────────────────────────┐
│  JFK → LAX          [One Way badge]               │
│  Jun 1 – Jun 7      Alert: $299   Best: $249 ↓    │
│  Last checked: 2h ago        [History] [Delete]   │
└───────────────────────────────────────────────────┘
```
- Route: `text-xl font-semibold`
- Badge: shadcn `<Badge>` for trip type
- Alert threshold vs best price: color-coded (`text-green-600` when best < threshold)
- Price drop indicator: down-arrow icon when best < threshold
- Last checked: relative time (e.g., "2h ago") using `Intl.RelativeTimeFormat`
- "History" button: outline variant with `ChevronDown`/`ChevronUp` icon that rotates when expanded
- "Delete" button: destructive variant (red outline), confirm via shadcn `AlertDialog` instead of `window.confirm()`

**History expansion:**
- Inline `<Accordion>`-style animated expand
- Recharts line chart with styled axes, tooltip showing price+date on hover
- Chart height: 200px

Acceptance: Empty state renders when no searches; price color coding works; delete uses dialog not window.confirm.

---

## 5. Accessibility Requirements

- All interactive elements meet WCAG 2.1 AA color contrast (≥4.5:1 for text)
- All `<button>` elements have visible focus rings (`focus-visible:ring-2 focus-visible:ring-sky-400`)
- Dialog closes on Escape key (shadcn Dialog handles this)
- Skeleton loading regions have `aria-hidden="true"` since they convey no content
- Color alone is never the only signal (badges always have text labels alongside colors)

---

## 6. Responsive Breakpoints

Minimum supported width is 768px (unchanged from m01/m02). At 768px+:
- Two-column airport row
- Two-column date row
- Flight cards are single column (full width)
- Nav bar stays horizontal (no hamburger)

At <768px: layout is allowed to be imperfect (not a stated goal).

---

## 7. Non-Goals (Explicitly Out of Scope)

- No backend changes
- No new features or data
- No new routes
- No dark mode
- No animations beyond CSS transitions (no Framer Motion)
- No mobile/responsive below 768px
- No unit test changes for existing logic (tests may need import path or snapshot updates, but logic stays the same)
- No custom icon design; use Lucide library only

---

## 8. Success Criteria

The milestone is complete when:

1. **Visual**: App has a coherent color scheme, typography, and spacing — no unstyled HTML elements visible to the user.
2. **NavBar**: Brand logo + nav links styled, active route visually highlighted.
3. **SearchForm**: Card layout, pill trip-type toggle, side-by-side date inputs, spinner on submit.
4. **FlightCards**: Price prominent and in brand color, airport codes large, stops badge colored.
5. **Loading skeletons**: 3 skeleton cards shown while search is in-flight.
6. **PriceGrid**: Color-coded heatmap visible.
7. **Track modal**: shadcn Dialog with backdrop; inline validation errors.
8. **TrackedSearchesPage**: Empty state renders; cards show color-coded price comparison; delete uses AlertDialog.
9. **All existing tests pass** (no regressions to logic or API layer).
10. **shadcn/ui + Tailwind installed and configured** without breaking Vite build.

---

## 9. Implementation Notes for Architect

- Tailwind + shadcn/ui setup requires: `npm install tailwindcss postcss autoprefixer`, `npx tailwindcss init`, configure `vite.config.ts` to include PostCSS, add `@tailwind` directives to a global CSS file imported in `main.tsx`.
- shadcn/ui components are copied (not imported from npm) — `npx shadcn-ui@latest add button card badge dialog input label select skeleton separator tooltip alert-dialog`. Generated files go into `src/components/ui/`.
- Lucide React: `npm install lucide-react`.
- The `Inter` font can be loaded via a `<link>` in `index.html` (Google Fonts CDN) or via `@fontsource/inter` npm package. Prefer the npm package to avoid CDN dependency.
- Existing component files (`SearchForm/index.tsx`, `FlightCard.tsx`, etc.) are updated in-place — no file renames.
- The `PriceHistoryChart` component already uses Recharts; only styling changes needed (axis colors, tooltip style, line color).

---

## 10. Open Questions for Architect

1. **shadcn/ui init approach**: `npx shadcn-ui@latest init` modifies `tailwind.config.ts`, `globals.css`, and `components.json`. How should this be done in a worktree context — run the CLI or manually scaffold the config files?
2. **Tailwind + Vite integration**: Does the existing `vite.config.ts` need postcss plugin added, or is Tailwind v3 handled via the `@tailwindcss/vite` plugin (v4 approach)?  Check current Tailwind version and choose the correct integration.
3. **Test environment**: Vitest tests run in jsdom. Tailwind CSS is stripped at test time. Will shadcn/ui component imports (which reference CSS variables) cause test failures? If so, what's the mock/stub approach?
4. **`window.confirm` replacement**: The existing `TrackedSearchRow` uses `window.confirm()`. This should be replaced with shadcn `<AlertDialog>`. Does this require state changes to `TrackedSearchesPage` or can it be self-contained inside `TrackedSearchRow`?
