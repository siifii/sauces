# Build web-react

## Tokens
Follow the project's token system; never add a second one. New values go where tokens already live: the Tailwind v4 `@theme` block in the global CSS, Tailwind v3 `theme.extend` in `tailwind.config.*`, CSS custom properties in the token file (`tokens.css`), or the CSS-in-JS theme object. Components consume tokens only (`bg-brand`, `var(--color-brand)`, `theme.colors.brand`); an arbitrary-value color class (`bg-[#3D5AFE]`) is a hard-coded color. Use `rem` or the project's spacing scale, never fixed frame pixels for layout.

## Components
Function components in the project's TS/JS style, typed props, defaults kept when extending. Semantic elements first: `button` for actions, `a` for navigation, `label` tied to every field, `fieldset`/`legend` for groups, headings by document level, not by size. ARIA only where HTML has nothing. In the Next.js App Router keep presentational components server-compatible (no hooks, no event handlers) and add `'use client'` only to the smallest interactive leaf; in the Pages Router every component is a client component. Reuse the project's UI kit (shadcn/ui, MUI, Chakra, Mantine) when it matches; extend, wrap or ask before touching a user component. Never absolute-position content to copy a frame.

## Responsive
Build mobile-first from the narrowest designed width. Turn each `plan.breakpoints[]` entry into a `min-width` rule in the project's form: Tailwind variants (`md:`, or a custom screen added in `@theme --breakpoint-*` / v3 `screens` when the plan says so), CSS Module `@media (min-width: …)`, or the CSS-in-JS breakpoint helper. Use a container query (`@container`, Tailwind `@container`/`@md:`) only when the project already uses them or a component must adapt to its slot. With one design width: a fluid layout with max-width containers only.

## Previews and tests
Add a Storybook story per state when Storybook exists. With the project's runner (Vitest or Jest) and Testing Library, render each design state of the screen view through props, query by role and label, and render once in a right-to-left locale asserting `dir="rtl"`. A jsdom render is a test, not visual verification.

## Strings
Use the project's i18n library and its real catalogs: next-intl `messages/<locale>.json` with `useTranslations`/`getTranslations`, react-i18next `t()` with its locale JSON, react-intl `FormattedMessage`, or Lingui. Keys by feature and meaning. Plurals and placeholders in that library's format (ICU for next-intl/react-intl, `_one`/`_other` suffixes for i18next). Other locales get the source value and a translate TODO in the library's comment form or `.sauces/todos.json`; never invent a translation. With no i18n library, put copy in a typed per-feature messages module (`messages.ts`) and leave a `TODO(sauces)` to adopt the library the plan recommends.

## Assets
Reuse the project's icon library (lucide-react, Heroicons, MUI icons). Otherwise SVG as a component through the configured SVGR, or an inline SVG component with `currentColor`. Raster images: `next/image` in Next.js, `<img>` elsewhere, always with `width`, `height` and `alt` (`alt=""` when decorative). Mirror directional icons in RTL (`rtl:-scale-x-100` or a `[dir="rtl"]` rule).

## State
Follow the existing pattern (hooks, context, zustand, Redux Toolkit, TanStack Query, server actions). The screen is a presentational `<Name>View` that takes state as props, so every design state can be rendered by passing props. Wire it to its route (Next `app/<route>/page.tsx` or `pages/<route>.tsx`, the React Router route, or the Vite app's router). Leave unknown behavior as `TODO(sauces)`.

## Folders
Follow the project: `components/`, `src/components/<Name>/`, `components/ui/` for kit primitives, feature folders when they exist. Route files stay in `app/` or `pages/`; shared components stay outside the route tree.

## Checks
Use the lockfile's package manager (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`, `bun install --frozen-lockfile`). Run the existing `lint`, `typecheck` (or the installed `tsc --noEmit` when TypeScript is configured), `test` and `build` (`next build` / `vite build`) scripts. Run `lint_generated.py --platform web-react` over the files you created or changed, with `--allow-colors` for the token files only: the `@theme` CSS file, `tailwind.config.*`, `tokens.css`, or the CSS-in-JS theme file.

## Don't
Never add Tailwind, a UI kit, CSS-in-JS, a router or a framework the project does not use unless the plan approved it. No inline `style` for design values, no hard-coded colors or strings, no physical `left`/`right`/`ml-*`/`pl-*`/`text-left` (use `ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`, logical CSS properties). No clickable `div`s, unlabelled inputs, or fixed-pixel frame layouts.
