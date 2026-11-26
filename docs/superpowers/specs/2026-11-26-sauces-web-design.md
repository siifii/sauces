# Sauces web targets: design

Date: 2026-11-26. Status: draft, awaiting the user's approval (builder check done 2026-11-26). This extends `docs/superpowers/specs/2026-11-24-sauces-v0.1-design.md` (the "v0.1 design"). Where the two disagree on web, this document wins; everything else in the v0.1 design still applies to web unchanged (three modes, plan gate, `.sauces/` state, report, localization as a headline strength, no bundled MCP).

## 1. Intent

The v0.1 design listed web targets as a non-goal. The user now wants Sauces to cover web too: **React projects and plain HTML/CSS/JS sites**, through the same pipeline (scan → ingest → plan → build → verify → report) and the same three modes (follow, advise, create).

The bar is the same as for mobile: a stranger's repo gets output its developer would merge without rewriting, done the way that stack's community considers good practice, with every string in the i18n system, layouts that work in RTL, and honest reporting when Sauces can't build or render something.

## 2. Goals, non-goals, anti-goals

**Goals**
- Two new platforms, `web-react` and `web-html`, each with its own scan, scaffold, build and verify references and its own lint rules, the way Flutter and React Native are separate today.
- **Responsive design as a first-class input.** Web designs often arrive as several frames of one screen at different widths (desktop, tablet, mobile). Ingest groups them by screen and breakpoint; plan maps them onto the project's breakpoints; verify renders each state at each designed width.
- Localization and RTL at least as strong as mobile: strings in the project's catalogs, `<html lang dir>` set by the i18n layer, CSS logical properties, mirrored directional icons, one RTL render per screen.
- Accessibility as part of "good practice" on web: semantic elements, labelled controls, visible focus, keyboard reachability. (The design audit already checks contrast.)
- Real render-and-diff verification on both platforms with Playwright (Chromium, headless), scored by the existing `scripts/visual_diff.py`.

**Non-goals (this round)**
- Vue/Nuxt, Svelte/SvelteKit, Angular, Solid. Vue is the next platform after this one.
- Server-side templates (Django/Jinja, Rails ERB, PHP/Blade, Go templates), CMS themes (WordPress, Shopify Liquid), HTML email. Scan recognizes them and says they're unsupported instead of guessing.
- React Native Web: it stays under `react-native`.
- SEO/meta tags, analytics, data fetching, routing setup beyond hosting the new screen, page-transition animation.

**Anti-goals** (failure even if it technically works)
- Absolute-positioned or fixed-pixel layouts copied from a Figma frame, which break at any width other than the frame's.
- `div` soup: clickable `div`s, inputs without labels, headings chosen by size instead of level.
- Adding Tailwind, a UI kit, a CSS-in-JS library or a framework to a project that doesn't use it, without the user picking that in the plan.
- Inline `style` attributes or hard-coded colors/strings in generated code; physical `left`/`right` CSS in generated code.
- Claiming "verified" from a jsdom snapshot or a Storybook build that was never rendered in a browser.

## 3. Constraints

- Everything in the v0.1 design §3 and `CLAUDE.md` still holds. In particular, **plugin scripts stay Python 3 with only Pillow + numpy** (stdlib otherwise). Node tooling runs only inside the user's project (its own `package.json`) or via `npx` with the version pinned and the user's approval through the plan gate. Sauces never adds a Node runtime dependency to itself.
- Playwright runs from Node (`@playwright/test` or `npx playwright`). It is never a Python dependency of the plugin.
- On the dev machine (checked 2026-11-26): `node` and `npx` are installed, and Playwright's Chromium 1228 browser is already cached. Fixture tests that need Node skip cleanly without it, as the RN tests do.

## 4. Approaches

**How to model web** *(the user approved option A, 2026-11-26)*
- **A. Two platforms, `web-react` and `web-html` (chosen).** Each has its own four references and lint rules. More files, but each stack's guidance stays specific and every SKILL.md stays under ~2,000 words.
- B. One `web` platform with stack sections. Rejected: React and plain-HTML practice mix in one reference, and "what is a component" gets muddy.
- C. Plain HTML as pages only, no components. Rejected: no reuse, no component graph or reuse stats, which is what Sauces is for.

**Which stacks** *(the user said "React, and also HTML and CSS, etc."; "etc." read as vanilla JS plus static-site setups; Vue and others are next)*: React via Next.js and Vite; plain HTML/CSS/JS, following Eleventy or Astro when a site already uses them.

## 5. Design

### 5.1 Platforms and detection

| Platform | Recognized by | Follows |
|---|---|---|
| `web-react` | `react` + `react-dom` in a `package.json` that has an app entry: Next.js (`next` + `app/` or `pages/`), Vite (`vite` + `index.html` mounting React), React Router framework mode | App Router vs Pages Router; styling (Tailwind v3 config / v4 `@theme`, CSS Modules, styled-components/Emotion, plain CSS); UI kit (shadcn/ui, MUI, Chakra, Mantine…); i18n (next-intl, react-i18next, react-intl/FormatJS, Lingui); tests (Vitest/Jest + Testing Library); Storybook |
| `web-html` | HTML pages with no React/Vue/Svelte/Angular app entry: plain static folders, Vite vanilla, Eleventy (`.eleventy.js`/`eleventy.config.*` + Nunjucks/Liquid partials), Astro (`astro.config.*`, `.astro` components) | Existing partials/components, CSS architecture (BEM, utility classes, layers), token files, existing i18n (per-locale pages or a JSON loader), icon approach |

- Scan reads config **without executing it** (same rule as RN). A repo with both a web app and a mobile app is already modelled as several entries in the profile's `projects[]`; cook asks which one when the design doesn't make it obvious.
- Add `web-react` and `web-html` to the platform enums in `profile-schema.json` and `plan-schema.json`, to `lint_generated.py`, and to `eval.py`.

### 5.2 Responsive breakpoints (shared)

- **Ingest:** each design source gets a `viewport` (CSS px width, and the device pixel ratio when known: Figma frame size, PNG size ÷ stated or inferred DPR). Frames of the same screen at different widths are grouped as `<screen>@<width>` (e.g. `login@390`, `login@1440`), using the same confirm-with-the-user step ingest already has for ambiguous grouping. Mobile platforms ignore the field.
- **Plan:** records `breakpoints[]`. Follow the project's own (Tailwind `screens`, custom media, existing `min-width` queries, a breakpoint token file). With none, go mobile-first with `min-width` queries at the widths the design provides, and say so in the plan. Container queries are fine where the project already uses them or a component has to adapt to its slot rather than the viewport.
- **One frame only:** build it fluid (no fixed widths beyond max-width containers), verify at that width, and list the other widths as "not designed, not verified" in the report rather than inventing layouts for them.
- Mobile platforms are unaffected: they never see web sample frames (5.8 keeps them in a separate folder), and a mobile run that is handed several widths of one screen keeps the frame closest to the target device width instead of the highest-resolution one *(Claude's call, from the builder check)*.

### 5.3 `web-react`

- **Components:** function components in the project's TS/JS style. In Next.js App Router, keep reusable presentational components server-compatible; add `'use client'` only on the smallest interactive leaf. Reuse the project's UI kit components when they match (the existing reuse/extend/wrap/new matching rules apply). Semantic elements first (`button`, `a`, `label`, `fieldset`), ARIA only where HTML has nothing.
- **Screens:** a route entry (Next `app/<route>/page.tsx`, a React Router route, or the Vite app's existing router) that renders a presentational `<Screen>View` taking state as props. Each design state (default/error/loading…) is reachable by passing props, which is what verify and tests seed.
- **Styling and tokens:** follow the project. New tokens go where the project keeps them: CSS custom properties, Tailwind theme (`@theme` in v4, `theme.extend` in v3), or the CSS-in-JS theme object. Arbitrary-value color classes (`bg-[#3D5AFE]`) count as hard-coded colors. Use logical properties and Tailwind's logical utilities (`ms-*`, `me-*`, `ps-*`, `pe-*`, `start-*`, `end-*`, `text-start`).
- **Strings:** the project's i18n library and its real catalogs, keys named by feature and meaning, ICU plurals/placeholders in that library's format, other locales get the source value plus a translate TODO (same rule as mobile; never invent a translation). With no i18n library, put copy in a typed per-feature messages module and recommend a library in the plan (react-i18next for Vite, next-intl for Next) as an advise item.
- **Assets:** reuse the project's icon library (lucide-react, Heroicons, MUI icons…). Otherwise SVG components through the configured SVGR, or `<img>`/`next/image` for raster with `width`/`height` set. Directional icons get an RTL mirror (`rtl:-scale-x-100` or a `[dir=rtl]` rule).
- **Previews and tests:** a Storybook story per state when Storybook exists; a Testing Library test that renders each state and one RTL locale with the project's runner.
- **Checks:** the lockfile's package manager; existing `lint`, `typecheck` (or the installed `tsc --noEmit`) and `test` scripts; `build` (`next build` / `vite build`); `lint_generated.py --platform web-react`.

### 5.4 `web-html`

- **Follow first.** If the site has a component system (Astro components, Eleventy/Nunjucks partials or macros, existing custom elements), new components are made in that system.
- **No component system:** components are **autonomous custom elements in light DOM** *(Claude's call: light DOM keeps the site's global CSS and tokens working and keeps forms and labels working natively; shadow DOM would cut both off)*. Each component is `components/<name>/<name>.js` (registers `<x-name>`, prefix taken from the project or the site name) plus `<name>.css`, both loaded with plain `<script type="module">` and `<link>`. No build step. Markup that matters without JS (headings, form fields, links) stays in the page HTML and the element enhances it; markup that is pure repetition is rendered by the element from its attributes.
- **Tokens:** CSS custom properties in `css/tokens.css` (or the site's existing token file), consumed by component CSS. Cascade layers only if the site uses them.
- **Strings:** follow the site's existing i18n (per-locale pages, an SSG i18n plugin, an existing loader). With none: `locales/<lang>.json` plus a small `i18n.js` that fills elements with `data-i18n="key"` and attributes listed in `data-i18n-attr="aria-label:key;placeholder:key2"`, sets `<html lang dir>`, and picks plural forms with `Intl.PluralRules` (`key.one`, `key.other`). The **source-locale text stays in the HTML** as the no-JS fallback; the lint allows text only on elements that carry `data-i18n`.
- **Assets:** an SVG sprite (`icons.svg` with `<symbol>`s, `<use href>`, `fill/stroke: currentColor`) unless the site already has an icon approach; raster images with `width`/`height`, `srcset`, and `<picture>` when the design has art direction.
- **Checks:** HTML parses cleanly (stdlib `html.parser` inside `lint_generated.py`, no unclosed tags in generated files); the page loads in Playwright with no console errors or failed requests; Astro/Eleventy sites also run their own build script; `lint_generated.py --platform web-html`.

### 5.5 Lint rules (`scripts/lint_generated.py`, stdlib only)

| Rule | `web-react` (`.js .jsx .ts .tsx .css .scss`, CSS Modules) | `web-html` (`.html .css .js`, `.njk .liquid .astro`) |
|---|---|---|
| `hardcoded-color` | hex/`rgb()`/`hsl()`/`oklch()` in `style={{}}`, styled/Emotion templates, CSS files; Tailwind arbitrary color classes | the same literals in CSS, `style=""` and JS, outside the token files |
| `hardcoded-string` | literal JSX text children; literal `aria-label`, `alt`, `title`, `placeholder` | text nodes and those attributes on elements without `data-i18n` / `data-i18n-attr` (or the site's own mechanism when following) |
| `physical-direction` *(new)* | `margin-left/right`, `padding-left/right`, `left:`/`right:`, `text-align: left/right`, `border-left/right`; Tailwind `ml-/mr-/pl-/pr-/left-/right-/text-left/text-right` | the same in CSS and `style=""` |
| `inline-style` *(new)* | — (style objects are covered by the color rule) | `style=""` attributes in generated HTML |
| `a11y-basic` *(new)* | `<img>` without `alt`; `onClick` on `div`/`span`; `<input>`/`<select>`/`<textarea>` with neither an `id` a `<label htmlFor>` points at, a wrapping `<label>`, nor `aria-label(ledby)` | the same in HTML (`for`, wrapping `<label>`) |

Token files (`--allow-colors`) skip only `hardcoded-color`, as today. `transparent`, `currentColor`, `inherit` and CSS variables are always allowed. `physical-direction` stays specific to web this round.

**Accessibility gating** *(Claude's call)*: `a11y-basic` blocks like the other rules. Visible focus and keyboard order are build-reference guidance, plus one Playwright check in verify that Tab reaches every interactive element of each screen (reported, not blocking). axe-core is not added this round: it would be one more Node dependency to approve; it is a candidate for the next round.

### 5.6 Verify (shared)

- **Runner:** reuse the project's Playwright if it has one (`@playwright/test`); write the Sauces spec under the project's existing e2e folder in `sauces/`. Otherwise add `@playwright/test` as a pinned devDependency, but only after the user approves it in the plan (a dependency change, same as mobile §5.6). `web-html` sites with no `package.json` use `npx -y playwright@<pinned>` against a stdlib `python3 -m http.server` serving the site root, so no `package.json` is created.
- **Seeding each state,** in order of preference: existing Storybook story → an existing fixture/test route → a dev-only fixture page Sauces generates (listed in the plan and in `generated_files`; for Next under a route guarded to development, for Vite an extra HTML entry that dev serves and the build ignores, for `web-html` a page under `.sauces/verify/fixtures/` that loads the real components and CSS) → manual checklist, said plainly.
- **Capture:** Chromium, viewport width from the design frame, `deviceScaleFactor` from the reference DPR, `reducedMotion: 'reduce'`, animations disabled, wait for `document.fonts.ready` and the state's readiness selector, full-page screenshot. One RTL pass per screen at the narrowest designed width (Arabic or pseudo-locale through the project's i18n). Two passes for the determinism check, as today.
- **Score:** `visual_diff.py` per `<screen>@<width>--<state>`, unchanged. The scored capture is **clipped to the design frame's exact width × height** (viewport = frame size), so the script's resize-to-reference never distorts a fluid page *(Claude's call: it keeps the shared script and mobile baselines untouched)*. A separate full-page capture goes in the report; if the page's content is taller or shorter than the frame by more than 10%, that is a non-blocking layout finding. Threshold 90, max 3 fix iterations, unchanged.
- **Browser:** the Chromium download (~150 MB on a machine without it) is part of the Playwright approval at the plan gate, stated with its size. Declined or offline → manual checklist, said plainly. In eval mode `.sauces/eval-approve` covers it, as it covers other test dependencies.

### 5.7 Scaffold (create mode)

- **`web-react`** *(Claude's call)*: Vite + React + TypeScript (`npm create vite@latest web-app -- --template react-ts`, confirming the installed CLI's flags first), CSS Modules + CSS custom-property tokens (no extra dependency), react-i18next with English plus the selected locales, Vitest + Testing Library, Playwright for verify. Next.js instead when the user asks for it (`--next`, App Router, next-intl). *Why Vite by default:* create mode builds a minimal shell to host the UI, and Vite is the smaller, client-only shell with the fastest verify; a framework choice is the user's to make.
- **`web-html`**: a static folder with no build step: `index.html`, `css/tokens.css`, `css/base.css`, `components/`, `locales/en.json` (+ selected locales), `i18n.js`, `icons.svg`, and a README section on serving it with any static server.
- Both add the standard Sauces scaffold README section and rescan after the overlay exists, as the mobile scaffolds do.

### 5.8 Fixtures and sample design

- `examples/targets/web-react-vite/`: Vite + React + TS, react-i18next, CSS Modules, a Button, TextField and Card, with deliberate gaps (one hard-coded color, one `margin-left`) for advise mode. Buildable with `npm ci && npm run build`.
- `examples/targets/web-react-next/`: Next.js App Router, Tailwind v4, next-intl, the same three components and one gap. Buildable.
- `examples/targets/web-html/`: a static site with `tokens.css`, two custom elements, the `data-i18n` loader, and one gap.
- `examples/designs/login-web/` *(new, separate from the mobile sample so mobile runs and baselines don't change)*: the existing 390 px PNGs plus **desktop frames** (1440 × 900, DPR 1, rendered from `login/src/` with a desktop stylesheet) for default, error and loading, so the web sample has two breakpoints, `login@390` and `login@1440`. Its own `description.md` with the same exact copy. `examples/designs/login/` is untouched.
- The empty target is reused for create mode (`--create-platform web-react|web-html`).

### 5.9 Docs and metadata to update

`spec.md` §7 (drop "Web targets" from non-goals; add a pointer here), the v0.1 design §2 non-goals line (pointer here), `CLAUDE.md` supported-targets table, `README.md`, `plugin.json` description and keywords (`react`, `nextjs`, `html`, `css`, `web`), and the platform lists in skills that enumerate platforms (cook, scan-project, scaffold, build, verify). The `report` skill gains a "Breakpoints" line per screen (designed, built, verified).

### 5.10 Build order

1. **Shared foundations:** schema enums, ingest `viewport` + breakpoint grouping, plan `breakpoints[]`, lint rules for both platforms with tests, Playwright verify path, desktop sample frames.
2. **`web-react`** end to end on the Vite fixture (follow, advise, create), then the Next fixture.
3. **`web-html`** end to end (follow, advise, create).
4. Docs and metadata (5.9), eval rows for the three web fixtures.

Each step ends with the usual exit check: `claude plugin validate` passes, the new tests pass, the platform's eval rows pass (builds, renders, zero hard-coded colors/strings/physical directions, fidelity ≥ 90 on the shipped sample at **both** breakpoints).

### 5.11 Eval

`eval.py` gains the two platforms in `SOURCE_EXTENSIONS` and `--create-platform`. Default build command per platform: `web-react` runs the lockfile's package manager `ci` + `build` (+ `typecheck` when present); `web-html` runs the HTML parse check and the Playwright load check (no console errors). Fidelity is scored per breakpoint; a row passes only when every designed breakpoint is ≥ 90.

## 6. Left to the builder

- Exact JSON field names for `viewport` and `breakpoints[]`, as long as they carry what 5.2 describes.
- The pinned Playwright version, and how the Sauces Playwright spec is laid out.
- The custom-element prefix rule when the site has none, and the exact `i18n.js` code (it must stay small and dependency-free).
- Lint regex details, as long as the rules in 5.5 hold and each has tests for hits and near-misses.
- How the desktop sample frames are rendered (headless Chromium from `src/` is the obvious path).
