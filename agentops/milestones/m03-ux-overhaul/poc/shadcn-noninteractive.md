# POC: shadcn/ui Non-Interactive Installation

## Question
Can `npx shadcn@latest init` be run non-interactively in a developer agent context (no TTY, no keyboard input)? What flags are required? What config files does it produce or require to already exist?

## Success Criteria
- `shadcn init` completes without hanging on interactive prompts
- All 10 required components (button, card, badge, dialog, input, label, select, skeleton, separator, tooltip, alert-dialog) are installed into `src/components/ui/`
- Build succeeds after installation
- All 98 existing tests still pass

## Approach
Added `baseUrl` and `paths: { "@/*": ["./src/*"] }` to `tsconfig.json` and a `resolve.alias` to `vite.config.ts` (required by shadcn). Ran: `npx shadcn@latest init --template=vite --yes --base=radix --preset=nova`. Then ran: `npx shadcn@latest add card badge dialog input label select skeleton separator tooltip alert-dialog --yes`. Finally ran `npm test`.

Key discovery: the Nova preset's auto-generated `src/index.css` uses `@import "shadcn/tailwind.css"` which contains `@theme inline { ... }` — this is Tailwind CSS v4 syntax that Tailwind v3 cannot process. The generated `* { @apply border-border outline-ring/50; }` line also fails because `border-border` is not a standard Tailwind v3 utility.

Fix: replace the Nova-generated `index.css` with a v3-compatible version that defines HSL CSS variables in `:root {}` and maps them to Tailwind colors via `tailwind.config.ts` `theme.extend.colors`.

## Results
- `shadcn init --template=vite --yes --base=radix --preset=nova` runs fully non-interactively
- All 11 component files created in `src/components/ui/` (button, card, badge, dialog, input, label, select, skeleton, separator, tooltip, alert-dialog)
- `components.json` created with correct aliases (`@/components`, `@/lib/utils`)
- `src/lib/utils.ts` created with `cn()` helper using `clsx` + `tailwind-merge`
- New runtime deps: `lucide-react`, `radix-ui`, `class-variance-authority`, `clsx`, `tailwind-merge`, `tw-animate-css`
- After replacing Nova CSS with v3-compatible `index.css` + updating `tailwind.config.ts` with color mappings: build succeeds (20.74 kB CSS output)
- 98/98 tests pass

## Conclusion
**Verdict:** VIABLE — with the following constraints:

1. `tsconfig.json` must have `baseUrl` and `paths: { "@/*": ["./src/*"] }` BEFORE running `shadcn init`
2. `vite.config.ts` must have `resolve.alias: { '@': path.resolve(__dirname, './src') }` BEFORE running `shadcn init`
3. Run: `npx shadcn@latest init --template=vite --yes --base=radix --preset=nova`
4. Run: `npx shadcn@latest add <components> --yes`
5. Replace the generated `src/index.css` with a v3-compatible version (HSL CSS variables, standard `@tailwind` directives)
6. Add CSS variable color mappings to `tailwind.config.ts` `theme.extend.colors`
7. The shadcn components use `import { X } from "radix-ui"` (new unified package, not `@radix-ui/react-*`)

## Limitations
- Did not verify dark mode CSS variables (not needed for this milestone — no dark mode in scope)
- Did not test all Radix-UI interactive behaviors (keyboard, focus, ARIA) — those are tested by the component library's own tests
