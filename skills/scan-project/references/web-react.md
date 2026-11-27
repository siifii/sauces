# Scan web-react

- Read `package.json`, lockfiles and workspace metadata without executing JS config (`next.config.*`, `vite.config.*`, `tailwind.config.*`, `postcss.config.*`): read them as text. The package manager is the lockfile's (`package-lock.json` npm, `pnpm-lock.yaml` pnpm, `yarn.lock` yarn, `bun.lock` bun).
- Classify first. A package with a runtime `react-native` or `expo` dependency is `react-native`, never `web-react`, even when it also has `react-dom` (Expo web). `web-react` needs `react` and `react-dom` plus an app entry:
  - Next.js: `next` with an `app/` folder (App Router) or `pages/` folder (Pages Router), at the root or under `src/`. Record which router; with both, App Router is primary and Pages Router legacy.
  - Vite: `vite` with an `index.html` whose module script mounts React (`createRoot`).
  - React Router framework mode: `@react-router/dev` with `app/routes` or `app/routes.ts`.
  A React component library without an app entry is not an app: report it in the summary, do not profile it.
- Follow the entry: the root layout (`app/layout.tsx`, `app/[locale]/layout.tsx`), `pages/_app.tsx`, or `src/main.tsx` → `App`. Note providers (theme, i18n, query client, store).
- Styling and tokens. Record the styling system in `architecture` evidence and set `theme.tokens_source` to the file that defines tokens:
  - Tailwind v4: the CSS file with `@import "tailwindcss"` and an `@theme` block (often `app/globals.css` or `src/index.css`).
  - Tailwind v3: `tailwind.config.*` `theme.extend`.
  - CSS custom properties: the file defining `:root { --… }` (for example `src/theme/tokens.css`), imported by the global stylesheet.
  - CSS Modules (`*.module.css`), styled-components or Emotion: the theme object passed to `ThemeProvider`, or the token CSS file.
  Set `theme.location` to the folder holding those files.
- UI kit: record shadcn/ui (`components.json` + `components/ui/`), MUI (`@mui/material`), Chakra, Mantine, Radix or Headless UI in `architecture` evidence. Treat kit components the project wraps as reusable components.
- State: record the real pattern: `hooks` (useState/useReducer/context), `zustand`, `redux-toolkit`, `jotai`, `tanstack-query` for server state, or Next server components with server actions.
- Components: list reusable components from `components/`, `src/components/`, `ui/` and design-system packages, with prop names from their TypeScript types. Exclude route entries (`page.tsx`, `layout.tsx`, route modules) and screens. Record a Storybook story only when the component has one (`*.stories.tsx`).
- Localization: `system: "js-i18n"` for next-intl (`messages/<locale>.json`, `i18n/request.ts`, `i18n/routing.ts`), react-i18next / i18next (`locales/*.json`, the `init` call), react-intl / FormatJS, or Lingui (`.po`). Set `location` to the catalog folder, `locales` from the catalog files or the routing config, and `rtl: true` when any locale is right-to-left (`ar`, `he`, `fa`, `ur`) or the code sets `dir="rtl"`. With no library, `system: "none"`.
- Tests: Vitest or Jest with Testing Library (`@testing-library/react`); note the `test` script.
- Screenshot tooling: record Playwright (`@playwright/test` + `playwright.config.*`) or Storybook test runner only when installed and runnable from a script. Next's or Vite's dev server alone is not screenshot tooling.
- Run the Sauces linter with `--platform web-react` over the components you listed and review each match before reporting it as a finding.
