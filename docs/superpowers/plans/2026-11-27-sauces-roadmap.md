# Sauces roadmap: enhancements after web targets

Date: 2026-11-27. Work these one at a time, in order. Each item ends with its tests passing, `claude plugin validate .claude-plugin/plugin.json` passing, and a commit pushed to main. Items that need a design decision get a short spec in `docs/superpowers/specs/` before code. Mark an item done here (with the commit) when it lands.

Context: web targets landed on 2026-11-27 with 5/5 live web evals passing (README "Latest web baseline"). Sauces is a public plugin; quality on strangers' repos and visible proof matter more than demo polish (see the product-direction notes in the v0.1 design).

## 1. Proof: demo and sample report
- `assets/demo.gif`: a short loop built from a real run's artifacts (design reference → rendered capture → diff → RTL capture → report), made by a reproducible dev script (`scripts/dev/make_demo_gif.py`, Pillow only). At the top of the README.
- `docs/demo/report.html`: a real, self-contained report from a live run, scrubbed of machine paths, linked from the README (viewable through GitHub Pages once enabled).
- Done when: README shows the GIF and links the sample report; the script regenerates both from an eval results folder.

## 2. Resource organization (plan already written)
- Execute `docs/superpowers/plans/2026-11-26-sauces-resource-organization.md` (4 tasks: resource map and naming rules, ignore generated target output, remove local generated dirs, final validation).

## 3. Polish the known gaps
- `report.html` shows per-breakpoint results for web (designed widths, verified scores, "not designed, not verified").
- Lint: the Tailwind physical-utility rule no longer fires on prose inside strings ("left-to-right"): match only in class-like contexts (`className`, `class`, `clsx`/`cn`/`tw`/`cva` calls, template literals bound to them).
- Verify/build web references: clean up files a dev server creates in the user's project during verify (Next.js `AGENTS.md`), or report them, never leave them silently.

## 4. Release v0.2.0
- Bump `plugin.json`, the README badge and marketplace entry to 0.2.0; add `CHANGELOG.md` (0.1.0 mobile, 0.2.0 web + fixes); tag `v0.2.0`; GitHub release with notes.

## 5. CI
- GitHub Actions: default pytest + `claude plugin validate` on every push/PR; the `-m web` suite on PRs touching web paths; weekly scheduled `-m web`. README status badge. Live `cook` evals stay manual (they cost credits).

## 6. Localization as the headline
- Report: a translation-coverage panel (keys added, keys reused, TODO locales) and side-by-side LTR/RTL captures per screen.
- Verify: an optional pseudo-locale pass (accented, ~30% longer text) on every platform to catch truncation and hard-coded strings.

## 7. `/sauces:translate`
- New skill: fills `TODO(sauces): translate` entries in the project's real catalogs for chosen locales, marks every machine translation for human review in the platform's comment form and in `.sauces/todos.json`, never touches reviewed strings. Plan-gated like everything else.

## 8. Lite mode
- `cook --lite`: one width per screen, no determinism second pass, one fix iteration; for quick tries and smaller credit use. Report says plainly what was skipped.

## 9. Dark mode as a first-class state
- Ingest pairs light/dark frames of the same state; plan maps them to the project's dark theme; verify renders both. Mobile and web.

## 10. Figma variables to tokens
- When the Figma MCP is connected, read variables/styles and map them to tokens instead of sampling pixels; record the source per token. Still opt-in MCP; never bundled.

## 11. Update mode (design changed)
- `cook` on a project with an existing `.sauces/manifest.json` diffs new frames against the old references and plans only what changed (changed tokens, components, copy), leaving untouched screens alone.

## 12. Design-system mode
- Input: a whole Figma library or a component sheet. Output: the component library and tokens in the chosen design-system structure, with a preview/story per component, without screens.

## 13. Vue / Nuxt platform
- `web-vue` per the web design's "next platform" note: scan, scaffold (Vite + Vue + TS, Nuxt with `--nuxt`), build, verify (shares `web-capture.md`), lint rules for `.vue` SFCs, fixtures, eval rows.

## 14. Mobile baseline
- Record live eval baselines for the mobile platforms in the README the same way as web (follow + create per platform), fixing what the runs find.

## 15. Reach
- Official plugin directory: start organization verification (owner action), then submit.
- Draft a launch post (design → idiomatic code in your repo, screenshot-verified, RTL included) for the owner to publish.
