# Changelog

All notable changes to Sauces. Versions follow [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-27

### Added
- **Web platforms.** `web-react` (React 19 with Next.js App/Pages Router or Vite; Tailwind v3/v4, CSS Modules, CSS-in-JS; next-intl, react-i18next) and `web-html` (plain HTML/CSS/JS, Eleventy, Astro; custom elements in light DOM). Each has scan, scaffold, build and verify references.
- **Responsive designs.** Frames of one screen at several widths become `<screen>@<width>` screens; plan maps them to the project's breakpoints; verify scores every designed width and lists other widths as "not designed, not verified".
- **Playwright verify for the web**, pinned (1.61.1), with no `package.json` added to static sites. Captures are clipped to the design frame; a keyboard (Tab) reachability check is reported.
- **Web lint rules** in `lint_generated.py`: hard-coded colors and strings, physical directions (CSS, style objects, Tailwind utilities in class contexts), basic accessibility, inline styles and unclosed tags (stdlib HTML parser).
- `/sauces:scaffold react` (Vite, `--next` for Next.js) and `/sauces:scaffold html` (no build step).
- Sample design `examples/designs/login-web` (phone and desktop frames) and fixtures `web-react-vite`, `web-react-next`, `web-html`.
- Report: a Breakpoints table for web runs. Demo GIF and a hosted sample report.
- Eval: web platforms, per-breakpoint fidelity, and a recorded web baseline (5/5 PASS).

### Fixed
- Mobile workflow repairs from live runs: SwiftUI safe-area handling, the Compose Multiplatform iOS launch crash, right-to-left fallbacks for untranslated strings, Expo Android capture without Expo Go.
- `check_json.py` supports `if`/`then`/`else`.
- Eval no longer lints web build output (`dist/`, `.next/`, ...).

## [0.1.0] - 2026-11-26

### Added
- The pipeline: ingest, scan-project, plan (approval gate), build, verify, report, and `cook` to run it end to end with resume.
- Platforms: Flutter, Android Jetpack Compose, SwiftUI, Compose Multiplatform, React Native (Expo or bare).
- Follow, advise and create modes; design-system structure choice; design audit with cited guidelines.
- Localization and right-to-left as first-class: strings in the project's catalogs in every locale, RTL renders checked.
- Visual verification scored 0-100 with up to three fix rounds, and a self-contained HTML report.

[0.2.0]: https://github.com/siifii/sauces/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/siifii/sauces/releases/tag/v0.1.0
