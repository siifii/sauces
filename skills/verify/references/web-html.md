# Verify web-html

Follow `web-capture.md` in this folder for the runner, seeding order, capture settings, clip rule, RTL pass and keyboard check. This file adds what is specific to static sites.

## Render test
Seed each state with a page under `.sauces/verify/fixtures/<screen>--<state>.html` that links the site's real CSS and component scripts by relative path from the site root and sets the state's attributes (`error`, `busy`) or markup. When the real page already shows a state, capture the real page. Eleventy and Astro sites: build them with their own script first and serve the output folder (`_site/`, `dist/`), with fixtures copied into it.

## Run
With no `package.json`, serve the site root with `python3 -m http.server <free port> --bind 127.0.0.1` and run the pinned `npx -y -p playwright@…` command from `web-capture.md`; never create `package.json` or `node_modules` in the site. Use `?lang=<rtl locale>` (or the per-locale page) for the RTL pass. The page must load with no console errors and no failed requests. Stop the server when done.

## Fix
Apply fixes through the build reference (`skills/build/references/web-html.md`): token custom properties, logical properties and `min-width` media queries, never inline `style` attributes.
