# web-html (Sauces test fixture)

A small static site (plain HTML, CSS and JavaScript modules, no build step, no `package.json`) used by Sauces tests and evals as an existing `web-html` project.

- Components: autonomous custom elements in light DOM, `x-` prefix: `components/x-button/`, `components/x-card/` (`.js` + `.css`).
- Tokens: CSS custom properties in `css/tokens.css`; page styles in `css/base.css`.
- i18n: `i18n.js` (`setLocale(lang)`) with `locales/{en,ar}.json`. Elements carry `data-i18n` / `data-i18n-attr`; the English text stays in the HTML as the no-JS fallback. `?lang=ar` switches to Arabic (right-to-left).
- Icons: SVG sprite in `icons.svg`.

Run it with any static server, e.g. `python3 -m http.server` from this folder.

Deliberate gap (Sauces should not copy it): `x-card.css` positions its accent bar with the physical `left:`.
