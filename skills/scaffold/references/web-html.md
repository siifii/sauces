# Scaffold web-html

1. Create a static folder with no build step at `web-html/`: no `package.json`, no bundler, no framework. Nothing is installed.
2. Write the overlay:
   - `index.html`: `<html lang="en" dir="ltr">`, viewport meta, `<link>`s to `css/tokens.css`, `css/base.css` and each component's CSS, `<script type="module">` for each component, and an inline module that runs `setLocale(initialLocale())` from `./i18n.js`. A Home page with a heading, one labelled field and an action, every text element carrying `data-i18n` with the English text in the HTML as the no-JS fallback.
   - `css/tokens.css`: CSS custom properties for the design's colors, spacing, radii and type (the only file with color literals). `css/base.css`: page styles with logical properties only.
   - `components/<name>/<name>.js` + `<name>.css`: autonomous custom elements in light DOM with the `x-` prefix (or the name the user chose), registered with `customElements.define`.
   - `i18n.js`: copy `${CLAUDE_PLUGIN_ROOT}/examples/targets/web-html/i18n.js` unchanged (it exports `setLocale` and `initialLocale`, fills `data-i18n` and `data-i18n-attr`, sets `<html lang dir>`, uses `Intl.PluralRules`).
   - `locales/en.json` plus one file per selected locale with the same keys (English text, and an entry per file in `.sauces/todos.json`).
   - `icons.svg`: an SVG sprite with the design's icons as `<symbol>`s, used with `<svg><use href="icons.svg#name"></use></svg>`.
3. Run the build reference's Checks: `lint_generated.py --platform web-html --allow-colors "web-html/css/tokens.css"` over every file you wrote (no `html-parse` findings), then serve the folder with `python3 -m http.server` and load it once with the pinned Playwright from the verify reference if it is already available; otherwise say the browser check waits for verify.
4. Append the standard Sauces scaffold README section to `web-html/README.md`, explaining that there is no build step and the site is served with any static server (`python3 -m http.server` from `web-html/`, then `?lang=ar` for right-to-left). Record `web-html` and rescan only after the overlay exists.
