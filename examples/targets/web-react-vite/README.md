# web-react-vite (Sauces test fixture)

A small React 19 + Vite + TypeScript app used by Sauces tests and evals as an existing `web-react` project.

- Components: `src/components/{Button,TextField,Card}/` (`.tsx` + CSS Modules).
- Tokens: CSS custom properties in `src/theme/tokens.css`.
- i18n: react-i18next, `src/i18n/index.ts`, catalogs in `src/i18n/locales/{en,ar}.json` (Arabic is right-to-left).
- Screen: `src/screens/HomeScreen.tsx` (`HomeView` takes its state as props).
- Tests: Vitest + Testing Library (`npm test`).

Scripts: `npm run build`, `npm run typecheck`, `npm test`, `npm run lint`.

Deliberate gaps (Sauces should not copy them): `Card.module.css` has one hard-coded color and one `margin-left`.
