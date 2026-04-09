# Research: Tailwind CSS v3 + shadcn/ui Setup

## Source: shadcn/ui Vite Installation Guide
https://ui.shadcn.com/docs/installation/vite

Key steps for Vite + React:
1. Create Vite project (already done)
2. Add Tailwind CSS: `npm install -D tailwindcss postcss autoprefixer`
3. Create `tailwind.config.js` and `postcss.config.js`
4. Add `@tailwind` directives to global CSS file
5. Edit `tsconfig.json` to add `baseUrl` and `paths` for `@/*` alias
6. Edit `vite.config.ts` to add `resolve.alias` for `@`
7. Run `npx shadcn@latest init`
8. Add components: `npx shadcn@latest add button card ...`

## shadcn CLI Non-Interactive Flags (verified in POC)
- `--template=vite` — selects the Vite framework template
- `--yes` — skips confirmation prompts (default: true)
- `--base=radix` — uses Radix UI component base
- `--preset=nova` — selects Nova preset (Lucide icons, Geist font)
- Component add: `npx shadcn@latest add <component> --yes`

## Tailwind v3 vs v4 Key Difference
- Tailwind v3: `postcss.config.js` with `tailwindcss` plugin (PostCSS-based)
- Tailwind v4: `@tailwindcss/vite` Vite plugin, no PostCSS config needed, uses `@import "tailwindcss"` directive

**Use v3 for this project** — simpler, no Vite plugin conflict, PRD specifies v3.

## shadcn Nova Preset + Tailwind v3 Compatibility Issue
The Nova preset generates CSS using `@theme inline {}` (Tailwind v4 syntax) and `@import "shadcn/tailwind.css"`. These are incompatible with Tailwind v3. Fix:
- Replace generated `index.css` with standard v3 CSS variable setup (HSL format)
- Add color mappings to `tailwind.config.ts` `theme.extend.colors`
- Map CSS variables like `border: 'hsl(var(--border))'`

## Component Import Pattern (shadcn Nova)
Components use the new unified `radix-ui` package (not individual `@radix-ui/react-*`):
```tsx
import { Dialog as DialogPrimitive } from "radix-ui"
```
This is different from the older shadcn style that used `@radix-ui/react-dialog`.

## Lucide React
- Installed automatically by shadcn Nova preset
- Import: `import { Plane, Bell, Loader2, ... } from 'lucide-react'`
- All icons used in PRD are available in lucide-react v0.x

## Inter Font via @fontsource
- `npm install @fontsource/inter`  
- Import in `main.tsx`: `import '@fontsource/inter/400.css'; import '@fontsource/inter/600.css';`
- Or use Google Fonts CDN link in `index.html` (simpler, no install)
