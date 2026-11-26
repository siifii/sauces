# Scan web-html

- Read config files as text, without executing them (`eleventy.config.*`, `.eleventy.js`, `astro.config.*`, `vite.config.*`, `package.json`). A site may have no `package.json` at all.
- Classify:
  - `web-html` needs at least one `.html` page (outside `node_modules/`, build output such as `dist/`, `_site/`, `build/`), or an Eleventy or Astro config, and no React, Vue, Svelte or Angular app entry.
  - A React app is `web-react` (see `web-react.md`); a React Native or Expo app is `react-native`.
  - A Vue, Nuxt, Svelte, SvelteKit, Angular or Solid app is unsupported: report "unsupported web framework (next platform)" with the evidence.
  - Server-template and CMS projects are unsupported: Django templates (`manage.py`, `templates/` with `{% block %}`), Rails (`Gemfile` with `rails`, `app/views/*.erb`), PHP or Laravel (`*.php`, `composer.json`, Blade), WordPress (`wp-config.php`, `wp-content/themes/`), Hugo/Jekyll themes with Go or Liquid server logic you cannot render. Report each as unsupported with the reason; never profile them as `web-html`.
- Kind of site, recorded in `architecture` evidence: plain static folder, Vite vanilla (`vite` with no framework plugin), Eleventy (Nunjucks `.njk` or Liquid partials in `_includes/`), or Astro (`.astro` components in `src/components/`).
- Components. Follow first: Astro components, Eleventy partials and macros, or existing custom elements (`customElements.define("x-name", …)`, light DOM or shadow DOM). Record the custom-element prefix when there is one. List each with its attributes or props. With none, write `components: []`.
- Tokens: set `theme.tokens_source` to the CSS file defining `:root { --… }` custom properties (`css/tokens.css`, `styles/variables.css`) or the Sass variables partial; `theme.location` to its folder. Note the CSS architecture (BEM, utility classes, cascade layers) in `architecture` evidence.
- State: `vanilla` (DOM and events), or the islands framework Astro uses for interactive parts.
- Localization: `system: "js-i18n"` when a JSON loader fills elements with `data-i18n` / `data-i18n-attr` from `locales/<lang>.json`, or an SSG i18n plugin is configured. Per-locale page folders (`/en/`, `/ar/`) with no loader also count as `js-i18n`; set `location` to those folders. Set `locales` from the catalog files or folders, and `rtl: true` when any is right-to-left (`ar`, `he`, `fa`, `ur`) or a page sets `dir="rtl"`. With none, `system: "none"`.
- Icons: an SVG sprite (`icons.svg` with `<symbol>`), inline SVG, or an icon font.
- Screenshot tooling: record Playwright only when a config and a runnable script exist. Do not create `package.json` or install anything during scan.
- Run the Sauces linter with `--platform web-html` over the pages and components you listed and review each match before reporting it.
