# POC: Tailwind CSS v3 + Vite 5 Integration

## Question
Does Tailwind CSS v3 install and build correctly in this Vite 5 project via the PostCSS plugin approach? Are the generated CSS utility classes present in the build output?

## Success Criteria
- `npm install tailwindcss@3 postcss autoprefixer` completes without error
- `npx vite build` produces a `.css` file containing Tailwind base styles and utility classes
- Existing 98 Vitest tests continue to pass after adding the CSS import in `main.tsx`

## Approach
Installed `tailwindcss@3.4.19`, `postcss`, and `autoprefixer` as devDependencies in a worktree copy of the frontend. Created `tailwind.config.ts` (content glob for `./src/**/*.{ts,tsx}`), `postcss.config.js` (tailwindcss + autoprefixer plugins), and `src/index.css` with the three `@tailwind` directives. Added `import './index.css'` to `main.tsx`. Ran `npx vite build` and `npm test`.

## Results
- `tailwindcss@3.4.19` installed correctly
- `npx vite build` produced `dist/assets/index-*.css` at 20.74 kB (gzip: 4.82 kB), containing Tailwind preflight reset and all utility classes referenced in source
- `npm test` ran all 98 tests: 12 test files passed, 0 failures — Tailwind CSS import in main.tsx is silently ignored by jsdom; no `css: true` Vitest config needed
- Key finding: `main.tsx` must explicitly import `'./index.css'` — the file is not auto-discovered

## Conclusion
**Verdict:** VIABLE

Tailwind CSS v3 integrates cleanly with Vite 5 via PostCSS. The setup requires three files: `tailwind.config.ts`, `postcss.config.js`, and `src/index.css`. The CSS import must be added to `main.tsx`. This approach does NOT require the Tailwind v4 `@tailwindcss/vite` plugin. Existing tests are unaffected.

## Limitations
- Only tested production build output; did not run `vite dev` server (HMR behavior not verified, but is a well-known working pattern)
- Did not test Tailwind JIT with very large class sets
