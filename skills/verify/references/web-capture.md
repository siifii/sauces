# Web capture (shared by web-react and web-html)

Read this from the platform's verify reference. It defines the runner, how each state is seeded, the capture settings, the clip rule and the keyboard check.

## Runner and approval

- Pinned version: **`playwright@1.61.1`** (Chromium). Use this exact pin everywhere below.
- **Project has Playwright** (`@playwright/test` in `package.json` with a `playwright.config.*`): use its installed version and browsers. Put Sauces files in the project's e2e folder under `sauces/` and run them with the project's package manager.
- **Project has a `package.json` but no Playwright:** add `@playwright/test@1.61.1` as a devDependency only if the approved plan lists that dependency change. Otherwise fall back to the `npx` path below, which adds nothing to the project.
- **`web-html` site with no `package.json`:** never create `package.json` or `node_modules` in the site. Serve the site root with the standard library and run the pinned Playwright through `npx -y`:

  ```bash
  python3 -m http.server <free port> --bind 127.0.0.1   # from the site root, in the background
  ```
- **Browser download:** Playwright's Chromium is about 150 MB on a machine that does not have it. It is part of the Playwright approval at the plan gate, stated with its size. If the user declined, or the machine is offline, write the manual checklist (verify SKILL §6) and say plainly why. In eval mode `.sauces/eval-approve` covers the download.

## Seeding each state

Use the first that exists, per state:

1. An existing **Storybook** story for the screen state (`iframe.html?id=<story-id>` on the running Storybook).
2. An existing fixture or test route the project already has.
3. A **dev-only fixture page** Sauces generates. List it in the plan and record it with `sauces_state.py add-files generated`:
   - Next.js: `app/sauces-fixtures/<screen>/page.tsx` (or `pages/sauces-fixtures/<screen>.tsx`) that renders the `<Screen>View` with the state from `?state=`, and calls `notFound()` when `process.env.NODE_ENV !== "development"`, so production never serves it.
   - Vite: an extra HTML entry `sauces-fixtures.html` mounting the view with the state from `?state=`. The dev server serves it; the build ignores it because `build.rollupOptions.input` lists only the real entries (add that list if the config has none, as part of the approved plan).
   - `web-html`: a page under `.sauces/verify/fixtures/<screen>--<state>.html` that links the site's real CSS and component scripts by relative path and sets the state's attributes. Serve the site root so those paths resolve.
4. **Manual checklist**, said plainly: the state is not verified.

Serve dev fixtures with the project's dev server (`next dev`, `vite`) or a static server; wait until it answers before capturing.

**Leave no dev-server files behind.** Before starting the server, list the project's untracked files (`git status --porcelain --untracked-files=all`, or a file listing without git). After stopping it, compare: a file the server created (for example `AGENTS.md` or `next-env.d.ts` written by `next dev`) that is not one of Sauces' recorded files is removed, and the summary says which files were removed. Never remove a file that existed before verify started.

## Capture

Write this script to `.sauces/verify/capture.cjs` (Sauces output, deleted with the folder) and run it once per state and pass:

```js
// Sauces verify capture. node capture.cjs <url> <out.png> <width> <height> <dpr> [ready-selector]
const { chromium } = require("playwright");
const path = require("path");

(async () => {
  const [url, out, w, h, dpr, ready] = process.argv.slice(2);
  const width = Number(w);
  const height = Number(h);
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width, height }, deviceScaleFactor: Number(dpr), reducedMotion: "reduce",
  });
  const consoleErrors = [];
  const failedRequests = [];
  const ignored = (u) => new URL(u).pathname === "/favicon.ico";
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
  page.on("pageerror", (e) => consoleErrors.push(String(e)));
  page.on("requestfailed", (r) => { if (!ignored(r.url())) failedRequests.push(r.url()); });
  page.on("response", (r) => {
    if (r.status() >= 400 && !ignored(r.url())) failedRequests.push(`${r.status()} ${r.url()}`);
  });
  await page.goto(url, { waitUntil: "networkidle" });
  if (ready) await page.waitForSelector(ready);
  await page.evaluate(() => document.fonts.ready);
  // Freeze motion and hide dev-only overlays (Next.js dev indicator, Vite error overlay).
  await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}nextjs-portal,vite-error-overlay{display:none!important}" });
  await page.screenshot({ path: out, animations: "disabled", clip: { x: 0, y: 0, width, height } });
  await page.screenshot({ path: path.join(path.dirname(out), "full.png"), animations: "disabled", fullPage: true });
  const contentHeight = await page.evaluate(() => document.documentElement.scrollHeight);

  // Keyboard check: Tab through the page and list interactive elements never focused.
  const total = await page.evaluate(() => {
    const els = [...document.querySelectorAll(
      "a[href],button,input,select,textarea,summary,[tabindex],[onclick],[role=button],[role=link]")]
      .filter((e) => !e.disabled && e.type !== "hidden" && e.getAttribute("tabindex") !== "-1"
        && e.getClientRects().length > 0);
    els.forEach((e, i) => e.setAttribute("data-sauces-tab", String(i)));
    return els.length;
  });
  const reached = new Set();
  for (let i = 0; i < total + 5; i++) {
    await page.keyboard.press("Tab");
    const idx = await page.evaluate(
      () => document.activeElement?.closest("[data-sauces-tab]")?.getAttribute("data-sauces-tab"));
    if (idx != null) reached.add(idx);
  }
  const unreachable = await page.evaluate((seen) => [...document.querySelectorAll("[data-sauces-tab]")]
    .filter((e) => !seen.includes(e.getAttribute("data-sauces-tab")))
    .map((e) => e.outerHTML.slice(0, 120)), [...reached]);
  await browser.close();
  console.log(JSON.stringify({
    console_errors: consoleErrors, failed_requests: failedRequests,
    content_height: contentHeight, frame_height: height,
    height_off: Math.abs(contentHeight - height) / height > 0.1, unreachable,
  }));
})();
```

Run it without touching the project:

```bash
npx -y -p playwright@1.61.1 -c 'NODE_PATH="$(dirname "$(dirname "$(command -v playwright)")")" node .sauces/verify/capture.cjs "<url>" "<out.png>" <width> <height> <dpr> "<ready selector>"'
```

When the project has its own `@playwright/test`, run the same script with its installed `playwright` (`node .sauces/verify/capture.cjs …` from the project root) or port it to a spec under the e2e folder's `sauces/`.

Settings, per state of a `<screen>@<width>` screen:

- Viewport = the design frame's CSS size: width from `screens[].breakpoint`, height from the reference PNG height ÷ DPR. `deviceScaleFactor` = the reference's `sources[].viewport.dpr` (1 when unknown). `reducedMotion: 'reduce'`, animations and transitions disabled, wait for `document.fonts.ready` and the state's readiness selector (a test id or role the state shows, such as the error text).
- **Clip rule:** the scored image is clipped to the frame's exact width × height, so its PNG has the reference's pixel size and `visual_diff.py` never stretches a fluid page. Write it as `.sauces/verify/<screen>@<w>--<state>/iter-<n>/rendered.png`.
- The script also writes `full.png` (full page) beside it. It is for the report only, never scored. If `height_off` is true (content height differs from the frame height by more than 10%), add a non-blocking layout finding to the state's `remaining`.
- `console_errors` and `failed_requests` must be empty; otherwise fix them like a failing build (they usually are missing assets or a broken import) and say what was fixed.
- `unreachable` lists interactive elements that Tab never reached. Report each as one sentence in `remaining` (non-blocking); never claim keyboard access you did not check.
- Determinism: on iteration 1 capture each state twice (the verify SKILL `_render/a` and `_render/b` passes) with identical settings.

## RTL and breakpoints

- One RTL pass per screen, at the **narrowest** designed width only, in the project's right-to-left locale (Arabic, or a pseudo-locale) through its i18n (`/ar/` route, `?lang=ar`, or the i18n library's language switch). Copy it to `.sauces/verify/<screen>@<narrowest>--<state>/rtl.png` and check mirroring, logical spacing and clipping.
- Widths in the plan's `breakpoints[]` that have no design frame are reported as "not designed, not verified" for that screen. Never invent a reference for them and never score them.
- A design with one frame width: verify only at that width; every other project breakpoint is "not designed, not verified".
- Summary `renderer`: `"playwright"` (add the version and runner in the text after it when useful, e.g. `"playwright 1.61.1 (npx, http.server)"`).
