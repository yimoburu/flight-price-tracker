# POC: Vitest + Tailwind CSS + shadcn/ui Compatibility

## Question
After installing Tailwind CSS v3, PostCSS, and shadcn/ui components (which import from `radix-ui` and reference CSS variables), do existing Vitest tests still pass without any Vitest configuration changes?

## Success Criteria
- All 98 existing tests pass after Tailwind + shadcn installed
- No test failures from CSS import errors, CSS variable references, or Radix UI imports

## Approach
With Tailwind CSS v3 + PostCSS + shadcn/ui fully installed in the worktree (all 11 components in `src/components/ui/`, `src/index.css` imported in `main.tsx`), ran `npm test` twice: once immediately after Tailwind install, once after shadcn install. Captured pass/fail counts.

## Results
- After Tailwind only: 12 test files passed, 98 tests passed
- After shadcn + vite.config alias update: 12 test files passed, 98 tests passed
- Vitest's jsdom environment silently ignores CSS imports — `import './index.css'` does not cause errors
- Radix UI imports in `src/components/ui/*.tsx` are not imported by any existing test (tests mock at component level), so no runtime Radix issues in tests
- The `vite.config.ts` alias `@/*` is required for the shadcn components to resolve `@/lib/utils` — but since tests import application-level components (not shadcn ui components directly), the alias must be configured in both `vite.config.ts` and `tsconfig.json`

## Conclusion
**Verdict:** VIABLE

No changes to `vitest.config` are needed. The existing `test: { environment: 'jsdom', globals: true, setupFiles: ['src/setupTests.ts'] }` block in `vite.config.ts` handles Tailwind CSS correctly — CSS is silently ignored in tests. Adding the `resolve.alias` for `@/*` is required for the build to work (not just tests), but tests still pass without it if shadcn components aren't directly rendered in tests.

## Limitations
- Tests do not render any shadcn/ui components directly — they use the existing application components which will be updated in m03. If tests were updated to render `<Button>` etc., the CSS variable values would be empty strings (no rendered CSS), but the component logic would work.
- The `window.confirm` mock in `TrackedSearchRow.test.tsx` will need updating when `TrackedSearchRow` is updated to use `AlertDialog` instead of `window.confirm`. This is expected and noted in the task spec.
