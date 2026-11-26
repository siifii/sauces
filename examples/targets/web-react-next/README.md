# web-react-next (Sauces test fixture)

A small Next.js 16 App Router app used by Sauces tests and evals as an existing `web-react` project.

- Routing: `app/[locale]/layout.tsx` and `app/[locale]/page.tsx`, locales `en` and `ar` (right-to-left), `proxy.ts` for locale detection.
- Styling and tokens: Tailwind CSS v4, tokens in the `@theme` block of `app/globals.css` (`bg-brand`, `text-text-variant`, `rounded-m`, ...).
- i18n: next-intl, `i18n/request.ts`, catalogs in `messages/{en,ar}.json` (ICU plurals).
- Components: `components/{Button,TextField,Card}.tsx`; the screen is `components/HomeView.tsx` (state as props).

Scripts: `npm run build`, `npm run typecheck`, `npm run lint`.

Deliberate gap (Sauces should not copy it): `Card.tsx` uses the physical `ml-2` utility.
