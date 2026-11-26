# Build web-html

## Tokens
CSS custom properties in the site's token file (`css/tokens.css` or the existing one), consumed by component CSS with `var(--…)`. Add new values there only. Use cascade layers only when the site already does. No colors outside the token file.

## Components
Follow first: if the site has Astro components, Eleventy (Nunjucks/Liquid) partials or macros, or existing custom elements, make new components in that system and its naming. With none, make autonomous custom elements in light DOM (no shadow root, so global CSS, tokens, forms and labels keep working): `components/<name>/<name>.js` registers `<x-name>` (the site's existing prefix, else `x-`), plus `<name>.css`, loaded with `<script type="module">` and `<link rel="stylesheet">`; no build step. Markup that matters without JS (headings, form fields, labels, links) stays in the page HTML and the element enhances it; markup that is pure repetition is rendered by the element from its attributes. Semantic elements, labelled fields, real `button`s, visible focus.

## Responsive
Mobile-first CSS. Each `plan.breakpoints[]` entry becomes a `@media (min-width: …)` block in the component or page CSS, or the site's breakpoint custom media when it has one. Container queries only when the site uses them or a component must adapt to its slot. With one design width: fluid layout, max-width containers only.

## Previews and tests
Add a preview page per component state only if the site keeps one (a `styleguide.html` or Storybook for HTML); otherwise the page itself is the preview. Verification renders the real page in a browser.

## Strings
Follow the site's i18n: per-locale pages, an SSG i18n plugin, or an existing loader. With none, use `locales/<lang>.json` plus the small dependency-free `i18n.js` loader (the canonical one is `${CLAUDE_PLUGIN_ROOT}/examples/targets/web-html/i18n.js`; copy it): it fills elements carrying `data-i18n="key"` and attributes listed in `data-i18n-attr="aria-label:key;placeholder:key2"`, sets `<html lang dir>`, and picks plural forms with `Intl.PluralRules` (`key.one`, `key.other`, …) from `data-i18n-count`. The source-locale text stays in the HTML as the no-JS fallback; every element with text carries `data-i18n`. Other locales get the source value and a `TODO(sauces): translate` entry in `.sauces/todos.json`; never invent a translation.

## Assets
An SVG sprite (`icons.svg` with `<symbol>`s, referenced by `<svg><use href="icons.svg#name"></use></svg>`, `fill`/`stroke: currentColor`) unless the site has its own icon approach. Raster images with `width`, `height`, `alt`, `srcset`, and `<picture>` when the design has art direction. Mirror directional icons with a `[dir="rtl"]` rule.

## State
Vanilla DOM state inside the element (attributes and properties in, events out). Every design state is reachable by an attribute (`error`, `busy`) so verify can seed it. Leave unknown behavior as `TODO(sauces)`.

## Folders
Follow the site layout. Without one: `components/<name>/`, `css/`, `locales/`, `icons.svg`, pages at the root. Eleventy: `_includes/` for partials; Astro: `src/components/` and `src/pages/`.

## Checks
Run `lint_generated.py --platform web-html` over the files you created or changed, with `--allow-colors` for the token file only; its `html-parse` rule must report no unclosed tags. Load each page in Playwright (see the verify reference) and confirm there are no console errors or failed requests. Eleventy and Astro sites also run their own build script with the lockfile's package manager.

## Don't
Never add a framework, bundler, Tailwind or `package.json` to a no-build site unless the plan approved it. No shadow DOM for components that hold form fields or need global CSS. No inline `style` attributes, hard-coded colors or strings, or physical `left`/`right` CSS (use `margin-inline-start`, `inset-inline-start`, `text-align: start`). No clickable `div`s or unlabelled inputs.
