# Sauces Web Targets (`web-react`, `web-html`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sauces turns design sources into components for React (Next.js, Vite) and plain HTML/CSS/JS projects through the existing pipeline, with responsive breakpoints and real Playwright verification.

**Architecture:** Two new platform IDs plug into the same seams every mobile platform uses: schema enums, four references per platform (scan-project, scaffold, build, verify), rules in `scripts/lint_generated.py`, a fixture under `examples/targets/`, and eval wiring. Breakpoints are carried in the manifest as one screen per designed width (`login@390`, `login@1440`), so verify, report and eval keep treating "screen × state" as the unit and need no new loop.

**Tech Stack:** Markdown skills; Python 3 stdlib + Pillow + numpy scripts (`html.parser` for HTML lint); Node 20+ in fixtures only; React 19, Vite, Next.js App Router, Tailwind v4, next-intl, react-i18next, Vitest + Testing Library; Playwright (Chromium) for captures; pytest.

**Spec:** `docs/superpowers/specs/2026-11-26-sauces-web-design.md` (wins on web), on top of `docs/superpowers/specs/2026-11-24-sauces-v0.1-design.md` and `docs/superpowers/spec.md`. Read all three.

## Global Constraints

- Skills are imperative instructions for Claude; each SKILL.md body stays under ~2,000 words. `skills/ingest/SKILL.md` and `skills/build/SKILL.md` are already at ~2,100: add web detail to `references/`, never to their bodies, beyond a one-line pointer.
- Plugin scripts: `python3 -I`, stdlib + Pillow + numpy only, `--help`, self-contained (no sibling imports under `-I`). No Node dependency in the plugin itself.
- Node tooling runs only inside a target project or via `npx` with a pinned version, and only after plan-gate approval (design §3, §5.6).
- Platform IDs exactly `web-react` and `web-html`. Scaffold destinations `web-app/` (web-react) and `web-html/` (web-html). Scaffold argument words `react` / `web` → `web-react`, `html` → `web-html`; `--next` selects Next.js.
- Web manifest screen IDs are `<screen>@<css-width>`; state IDs stay `<screen-id>--<state>` (e.g. `login@1440--error`).
- Verify captures are clipped to the design frame's exact width × height at the reference DPR; full-page captures are report-only; a >10% content-height difference is a non-blocking finding.
- Fidelity threshold 90, max 3 fix iterations (unchanged). A web eval row passes only when every breakpoint's default state is ≥ 90.
- Generated web code has zero `hardcoded-color`, `hardcoded-string`, `physical-direction`, `a11y-basic` findings; `web-html` also zero `inline-style` and `html-parse`.
- Mobile behavior and the `examples/designs/login/` sample stay unchanged.
- Sample copy (verbatim): `Welcome back`, `Email`, `Password`, `Forgot password?`, `Sign in`, `Incorrect email or password`. Brand `#3D5AFE`, surface `#FFFFFF`, text `#1B1B1F`, error `#B3261E`.
- **Copilot works in this tree.** Before a task that modifies `scripts/eval.py`, `tests/scripts/test_eval.py`, `skills/build/SKILL.md`, `skills/scaffold/SKILL.md`, or anything under `skills/build|scaffold|verify/references/`, run `git status --short` on those paths. If any are dirty and not yours, stop and ask the user to land Copilot's work first. Commit only your own paths (`git commit -- <paths>`), never `git add -A`.
- `claude plugin validate .claude-plugin/plugin.json` passes at the end of every task that touches plugin files. Finished work is merged/pushed to main.

## Review Focus

1. **An Expo app that also has `react-dom` (Expo web).** Expect `react-native`, never `web-react`. Pinned by the scan test in Task 7.
2. **Lint false positives on ordinary web code**: `#id` selectors, `color: var(--x)`, `currentColor`, `alt=""`, `margin-inline-start`, TS generics like `useState<string>("")`, Tailwind `bg-primary`, text that is only `{t("k")}` or only `{{ var }}`. Expect no findings. Pinned by near-miss tests in Tasks 1 and 2.
3. **A web design with a single frame width.** Expect a fluid build verified only at that width, and the report listing other widths as "not designed, not verified". Pinned by the reference test in Task 9 and the report test in Task 11.
4. **A `web-html` site with no `package.json`.** Expect verify to capture through `npx` + `python3 -m http.server` without creating `package.json` or `node_modules` in the site. Pinned by the opt-in capture test in Task 9.
5. **A mobile run handed the `login-web` sample (several widths per screen).** Expect ingest to keep the narrowest frame per state, not the 1440 one. Pinned by the ingest reference test in Task 3.

---

## File Structure

```
scripts/lint_generated.py                 + web-react / web-html rules, HTML linter (Tasks 1–2)
scripts/eval.py                           + platforms, builds defaults, per-breakpoint fidelity (Task 11)
skills/scan-project/SKILL.md              + two detection rows, platform order (Task 7)
skills/scan-project/references/{web-react,web-html}.md        (Task 7)
skills/scan-project/references/profile-schema.json            enum (Task 3)
skills/ingest/SKILL.md                    one-line pointer (Task 3)
skills/ingest/references/breakpoints.md   viewport, @width grouping, mobile narrowest rule (Task 3)
skills/ingest/references/manifest-schema.json  sources[].viewport, screens[].breakpoint/base (Task 3)
skills/plan/SKILL.md                      platform order + breakpoints step (Task 3)
skills/plan/references/plan-schema.json   enum + breakpoints[] (Task 3)
skills/build/references/{web-react,web-html}.md               (Task 8)
skills/verify/SKILL.md                    pointer to web capture rules (Task 9)
skills/verify/references/{web-react,web-html}.md, web-capture.md  (Task 9)
skills/verify/references/summary-schema.json  enum (Task 3)
skills/scaffold/SKILL.md + references/{web-react,web-html}.md (Task 10)
skills/report/SKILL.md                    Breakpoints line (Task 11)
examples/designs/login-web/               description.md, src/desktop.css, 6 PNGs (Task 4)
examples/targets/web-react-vite/          (Task 5)
examples/targets/web-react-next/          (Task 5)
examples/targets/web-html/                (Task 6)
tests/scripts/test_lint_web.py            (Tasks 1–2)
tests/skills/test_web_platforms.py        (Tasks 3, 7–11)
tests/fixtures/test_web_fixtures.py       opt-in `-m web` (Tasks 4–6, 9–10)
pytest.ini                                + `web` marker, excluded by default (Task 4)
docs, README.md, CLAUDE.md, plugin.json   (Task 12)
```

---

### Task 1: `web-react` lint rules

**Files:**
- Modify: `scripts/lint_generated.py` (RULES, EXTENSIONS, docstring, matching loop)
- Test: `tests/scripts/test_lint_web.py`

**Interfaces:**
- Produces: `lint_generated.py --platform web-react` over `.js .jsx .ts .tsx .css .scss`; rule IDs `hardcoded-color`, `hardcoded-string`, `physical-direction`, `a11y-basic`. A rule may opt in to matching **inside** string literals (needed for Tailwind classes); existing platforms keep today's behavior. A CSS-only rule set applies to `.css/.scss` files (color + physical-direction only), so the CSS helpers are reusable by `web-html` in Task 2.

- [ ] **Step 1: Write the failing tests** using the `lint`/`rules` helpers copied from `tests/scripts/test_lint_generated.py` with `platform="web-react"`:

```python
@pytest.mark.parametrize("rel,code,expected", [
    ("a.tsx", 'const s = {color: "#3D5AFE"};', [(1, "hardcoded-color")]),
    ("a.tsx", "const B = styled.button`\n  background: rgb(61 90 254);\n`;", [(2, "hardcoded-color")]),
    ("a.tsx", '<div className="bg-[#3D5AFE] p-4" />', [(1, "hardcoded-color")]),
    ("a.module.css", ".x { color: #fff; }", [(1, "hardcoded-color")]),
    ("a.css", ".x {\n  color: oklch(0.6 0.2 260);\n}", [(2, "hardcoded-color")]),
    ("a.tsx", "<h1>Welcome back</h1>", [(1, "hardcoded-string")]),
    ("a.tsx", "<p>Hello <b>{name}</b></p>", [(1, "hardcoded-string")]),
    ("a.tsx", '<input aria-label="Email" id="e" />', [(1, "hardcoded-string")]),
    ("a.tsx", '<img src={eye} alt="Show password" />', [(1, "hardcoded-string")]),
    ("a.css", ".x { margin-left: 8px; }", [(1, "physical-direction")]),
    ("a.css", ".x { text-align: right; float: left; }", [(1, "physical-direction"), (1, "physical-direction")]),
    ("a.tsx", "const s = {paddingRight: 4};", [(1, "physical-direction")]),
    ("a.tsx", '<div className="ml-2 text-left" />', [(1, "physical-direction"), (1, "physical-direction")]),
    ("a.tsx", "<img src={logo} />", [(1, "a11y-basic")]),
    ("a.tsx", "<div onClick={go}>{t('k')}</div>", [(1, "a11y-basic")]),
    ("a.tsx", "<input type=\"email\" />", [(1, "a11y-basic")]),
])
def test_web_react_hits(tmp_path, rel, code, expected): ...

@pytest.mark.parametrize("rel,code", [
    ("a.css", "#fade { color: var(--brand); }"),
    ("a.css", "a:hover #add {\n  color: currentColor;\n}"),
    ("a.css", ".x { margin-inline-start: 8px; border-color: transparent; }"),
    ("a.tsx", 'const [v, setV] = useState<string>("");'),
    ("a.tsx", "<h1>{t('login.title')}</h1>"),
    ("a.tsx", '<img src={d} alt="" />'),
    ("a.tsx", '<div className="bg-primary ms-2 text-start" />'),
    ("a.tsx", "if (a > b && c < d) go();"),
    ("a.tsx", '<input id="email" />\n<label htmlFor="email">{t("e")}</label>'),
    ("a.tsx", "// <h1>Old title</h1>"),
])
def test_web_react_near_misses(tmp_path, rel, code): ...  # returncode 0, no findings

def test_web_react_token_file_allows_colors(tmp_path):
    # --allow-colors "src/theme/**" on src/theme/tokens.css with "--brand: #3D5AFE;" → exit 0
    # same file with "margin-left: 1px" still → physical-direction
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/scripts/test_lint_web.py -q` — Expected: FAIL (`unknown platform: web-react`, exit 2).

- [ ] **Step 3: Implement** in `scripts/lint_generated.py`: add `"web-react"` to `RULES`/`EXTENSIONS`. Decisions the tests don't fix:
  - Hex colors in CSS count only in declaration values (after `property:` inside a block, up to `;`/`}`), never in selectors. In JS/TS, a hex or color function counts inside a string/template literal or a styled template.
  - Color functions: `rgb rgba hsl hsla hwb lab lch oklab oklch`. Named colors (`red`) are not flagged (too noisy); say so in the docstring.
  - JSX text: literal text with a letter between an opening tag `<Name …>` and the next `</` or `<Name`. A text run that is only `{…}` expressions is allowed.
  - `a11y-basic` in JSX: `<img` without `alt=`; `onClick` on `div`/`span`; `<input|select|textarea>` with none of `aria-label`, `aria-labelledby`, `id=` (with an `htmlFor` for it in the file), an enclosing `<label>` on the same or previous lines, or `type="hidden|submit|button"`. Document that JSX label matching is file-local.
  - Tailwind physical utilities: `ml- mr- pl- pr- left- right- border-l border-r rounded-l rounded-r text-left text-right float-left float-right` (with optional `-` and `sm:`-style prefixes), matched inside literals.
  - Update the module docstring with the web rules.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/scripts/test_lint_web.py tests/scripts/test_lint_generated.py tests/skills/test_mobile_platforms.py -q` — Expected: all PASS (existing platforms unchanged).

- [ ] **Step 5: Commit** `git commit -m "feat(lint): web-react rules" -- scripts/lint_generated.py tests/scripts/test_lint_web.py`

### Task 2: `web-html` lint rules and HTML linter

**Files:**
- Modify: `scripts/lint_generated.py`
- Test: `tests/scripts/test_lint_web.py`

**Interfaces:**
- Consumes: Task 1's CSS rule set.
- Produces: `--platform web-html` over `.html .htm .css .js .mjs .njk .liquid .astro`; rule IDs `hardcoded-color`, `hardcoded-string`, `physical-direction`, `inline-style`, `a11y-basic`, `html-parse`. Internal `lint_html(path, text, line_offset=0) -> list[dict]` built on `html.parser.HTMLParser`, used for markup files and for template literals in `.js/.mjs` that contain `<` (line numbers mapped back to the JS file).

- [ ] **Step 1: Write the failing tests** (`platform="web-html"`):

```python
@pytest.mark.parametrize("rel,code,expected", [
    ("index.html", "<h1>Welcome back</h1>", [(1, "hardcoded-string")]),
    ("index.html", '<input placeholder="Email" data-i18n-attr="aria-label:login.email">', [(1, "hardcoded-string"), (1, "a11y-basic")]),
    ("index.html", '<p style="color: red">{x}</p>', [(1, "inline-style")]),
    ("index.html", "<main>\n<section>\n<h1 data-i18n=\"t\">Hi</h1>\n</main>", [(2, "html-parse")]),
    ("index.html", '<img src="logo.svg">', [(1, "a11y-basic")]),
    ("index.html", '<div onclick="go()" data-i18n="k">Go</div>', [(1, "a11y-basic")]),
    ("css/site.css", ".x { padding-right: 2px; color: #B3261E; }", [(1, "hardcoded-color"), (1, "physical-direction")]),
    ("components/x-card/x-card.js", "this.innerHTML = `\n  <h2>Card title</h2>`;", [(2, "hardcoded-string")]),
    ("components/x-card/x-card.js", "el.style.color = '#fff';", [(1, "hardcoded-color")]),
])
def test_web_html_hits(tmp_path, rel, code, expected): ...

@pytest.mark.parametrize("rel,code", [
    ("index.html", '<h1 data-i18n="login.title">Welcome back</h1>'),
    ("index.html", '<p data-i18n="k">Hi <b>there</b></p>'),
    ("index.html", '<input id="e" placeholder="Email" data-i18n-attr="placeholder:login.email">\n<label for="e" data-i18n="login.email">Email</label>'),
    ("index.html", '<label data-i18n="l">Email <input type="email"></label>'),
    ("index.html", "<ul><li data-i18n=\"a\">A<li data-i18n=\"b\">B</ul>"),
    ("index.html", "<p>&nbsp;&copy; 2026</p>"),
    ("index.html", "<script>const s = 'Sign in';</script><style>.x{color:var(--c)}</style>"),
    ("index.html", "<!-- <h1>Old</h1> -->"),
    ("page.njk", "<h1>{{ t('login.title') }}</h1>"),
    ("Card.astro", "---\nconst { title } = Astro.props;\n---\n<h2>{title}</h2>"),
    ("index.html", '<img src="d.svg" alt="">'),
])
def test_web_html_near_misses(tmp_path, rel, code): ...
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/scripts/test_lint_web.py -q -k web_html` — Expected: FAIL (unknown platform).

- [ ] **Step 3: Implement.** Decisions the tests don't fix:
  - A text node needs `data-i18n` on itself or an ancestor element. Text with no letters (only whitespace, entities, digits, punctuation) is allowed. `<script>`/`<style>` content is skipped by the HTML linter (JS inside `.js` files is linted separately).
  - A translatable attribute (`aria-label alt title placeholder`) with letters must be listed in that element's `data-i18n-attr` (`attr:key;attr2:key2`).
  - `html-parse`: report unclosed non-void elements at their opening line, except optional-close elements (`p li dt dd tr td th thead tbody tfoot option optgroup colgroup caption rp rt`) and anything still open when the document's `html`/`body`/`head` close implicitly.
  - Template files: text made only of `{{ … }}`, `{% … %}` or `{ … }` (Astro) expressions is allowed. Skip an Astro frontmatter `---` block at the top. With `<!-- sauces-lint-ignore -->` on a line, suppress that line.
  - `a11y-basic` in HTML: `<img>` without `alt`; `onclick` on `div`/`span`; a form field with no `<label for>` matching its `id`, no enclosing `<label>`, no `aria-label`/`aria-labelledby`, unless `type` is `hidden|submit|button|reset`.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/scripts/test_lint_web.py tests/scripts/test_lint_generated.py tests/scripts/test_help.py -q` — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat(lint): web-html rules and HTML linter" -- scripts/lint_generated.py tests/scripts/test_lint_web.py`

### Task 3: Platform IDs, viewports and breakpoints in schemas, ingest and plan

**Files:**
- Modify: `skills/scan-project/references/profile-schema.json`, `skills/plan/references/plan-schema.json`, `skills/verify/references/summary-schema.json` (platform enums); `skills/ingest/references/manifest-schema.json`; `skills/ingest/SKILL.md` (one line in §3 Duplicates); `skills/plan/SKILL.md` (platform order; one step)
- Create: `skills/ingest/references/breakpoints.md`
- Test: `tests/skills/test_web_platforms.py`

**Interfaces:**
- Produces (schema fields, all optional so mobile manifests stay valid):
  - `sources[].viewport`: `{"width": int (CSS px), "dpr": number}`
  - `screens[].breakpoint`: int (CSS px width) and `screens[].base`: string (screen name without `@`), present only for web platforms; `screens[].id` is then `<base>@<breakpoint>`.
  - plan `breakpoints[]`: `{"name": str, "min_width": int, "source": "project" | "design"}`; required when `platform` is `web-react` or `web-html` (express with `if/then` in the schema).
- Platform order everywhere it's listed: `flutter, ios-swiftui, android-compose, kmp-cmp, react-native, web-react, web-html`.

- [ ] **Step 1: Write the failing tests** in `tests/skills/test_web_platforms.py`:

```python
WEB = ["web-react", "web-html"]

@pytest.mark.parametrize("platform", WEB)
def test_web_platform_in_enums(platform): ...   # same enum walk as test_mobile_platforms.py

def test_manifest_accepts_breakpoint_screens():
    # check_json.py validates a manifest with sources[0].viewport={"width":1440,"dpr":1}
    # and screens [{"id":"login@1440","base":"login","breakpoint":1440,...}] → exit 0
    # the existing tests/data/sauces_sample manifest still validates

def test_web_plan_requires_breakpoints():
    # a minimal plan with platform "web-react" and no "breakpoints" → check_json exit 1;
    # with [{"name":"desktop","min_width":1024,"source":"design"}] → exit 0;
    # platform "flutter" without breakpoints → exit 0

def test_ingest_breakpoint_reference():
    text = (REPO / "skills/ingest/references/breakpoints.md").read_text()
    for needle in ("viewport", "@", "narrowest", "web-react", "web-html", "not duplicates"):
        assert needle in text
    assert "references/breakpoints.md" in (REPO / "skills/ingest/SKILL.md").read_text()
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q` — Expected: FAIL.

- [ ] **Step 3: Implement.**
  - `breakpoints.md` tells ingest how to fill `viewport` (Figma frame size; PNG width ÷ DPR from the file name `@2x`, a description file, or inferred from common device/desktop widths, stated as a guess in `reason`), and that same-screen same-state frames with different viewport widths are **not duplicates**. It then says what to do with them: for `web-react`/`web-html` (from `.sauces/project-profile.json`, or the `--create-platform`/scaffold choice) make one screen per width with `id = <base>@<width>`; for every other platform keep the **narrowest** frame and record the others in `reason`.
  - `ingest/SKILL.md`: one sentence in §3 Duplicates pointing to the reference for frames with different widths. Don't grow the body otherwise.
  - `plan/SKILL.md`: add `web-react`, `web-html` to the platform order and one step: for web platforms, fill `breakpoints[]` per design §5.2 (project breakpoints first, else mobile-first at design widths; one width → fluid build, other widths reported as not designed). Keep the body under 2,000 words.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/skills -q -k "web_platforms or mobile_platforms or plan or ingest" && claude plugin validate .claude-plugin/plugin.json` — Expected: PASS; validate OK.

- [ ] **Step 5: Commit** the listed paths: `git commit -m "feat: web platform IDs, viewports and breakpoints" -- <paths>`

### Task 4: `login-web` sample design and the `web` test marker

**Files:**
- Create: `examples/designs/login-web/description.md`, `examples/designs/login-web/src/desktop.css`, `examples/designs/login-web/login@390--{default,error,loading}.png` (copies of the mobile PNGs), `examples/designs/login-web/login@1440--{default,error,loading}.png`, `tests/fixtures/test_web_fixtures.py`
- Modify: `pytest.ini` (`web: Node/Playwright-backed web fixture checks`; `addopts = -m "not skill and not mobile and not web"`), `tests/fixtures/test_designs.py`

**Interfaces:**
- Produces: the web sample at `examples/designs/login-web/` (Tasks 5–11 and eval use it); the `web` pytest marker; in `test_web_fixtures.py` the helpers `copy_web(name, tmp_path) -> Path` (copies `examples/targets/<name>` without `node_modules/.next/dist`) and `run(cwd, *cmd) -> bytes` (check=True, 900 s timeout), plus a module-level skip when `npx` is missing.

- [ ] **Step 1: Write the failing test** in `tests/fixtures/test_designs.py`:

```python
LOGIN_WEB = REPO / "examples" / "designs" / "login-web"

def test_login_web_design_files():
    for state in STATES:
        with Image.open(LOGIN_WEB / f"login@390--{state}.png") as im:
            assert im.size == (780, 1688)
        with Image.open(LOGIN_WEB / f"login@1440--{state}.png") as im:
            assert im.size == (1440, 900)
    text = (LOGIN_WEB / "description.md").read_text()
    for copy in ("Welcome back", "Email", "Password", "Forgot password?", "Sign in",
                 "Incorrect email or password", "1440", "390"):
        assert copy in text
    # the mobile sample is untouched
    assert sorted(p.name for p in LOGIN.glob("*.png")) == sorted(p.name for p in PNGS)
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/fixtures/test_designs.py -q` — Expected: FAIL (missing files).

- [ ] **Step 3: Create the sample.** `desktop.css` layers on `../login/src/login.css` (link both from the existing state HTML via a query-free copy or a `<link>` swap at render time): a 1440 × 900 canvas, a two-column layout (brand panel start side, form card end side, max-width ~420 px form), same tokens and copy. Render the three desktop PNGs with headless Chromium at viewport 1440 × 900, DPR 1, fonts from `../login/src/fonts/` loaded before capture. Use `npx -y playwright@<pinned> screenshot`, or the cached Chromium directly. Pin the version in `description.md`. `description.md` mirrors the mobile one: canvas sizes for both widths, files table, exact copy, colors, and a note that `@390` frames are copies of the mobile sample.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/fixtures/test_designs.py -q` — Expected: PASS. Open one desktop PNG and confirm by eye that the copy and colors match the description.

- [ ] **Step 5: Commit** `git commit -m "feat: login-web sample with desktop frames" -- examples/designs/login-web pytest.ini tests/fixtures/test_designs.py tests/fixtures/test_web_fixtures.py`

### Task 5: React fixtures (`web-react-vite`, `web-react-next`)

**Files:**
- Create: `examples/targets/web-react-vite/` and `examples/targets/web-react-next/`, each with `package.json`, `package-lock.json`, `README.md`, `.gitignore` (`node_modules`, `dist`, `.next`)
- Test: `tests/fixtures/test_web_fixtures.py`, `tests/skills/test_web_platforms.py`

**Interfaces:**
- Produces fixture layouts later tasks and eval rely on:
  - Vite: `src/components/{Button,TextField,Card}/` (`.tsx` + `.module.css`), `src/theme/tokens.css` (CSS custom properties), `src/i18n/index.ts` (react-i18next) + `src/i18n/locales/{en,ar}.json`, `src/App.tsx`, Vitest + Testing Library with `npm test`, scripts `build`, `typecheck`, `test`, `lint`. Gaps: one hard-coded color and one `margin-left` in `Card.module.css`.
  - Next: App Router `app/[locale]/page.tsx`, Tailwind v4 (`app/globals.css` with `@theme` tokens), next-intl (`messages/{en,ar}.json`, `i18n/request.ts`), `components/{Button,TextField,Card}.tsx`. Gap: one `ml-2` in `Card.tsx`. Scripts `build`, `typecheck`, `lint`.

- [ ] **Step 1: Write the failing tests**:

```python
# tests/skills/test_web_platforms.py
@pytest.mark.parametrize("name,files", [
    ("web-react-vite", ["src/components/Button/Button.tsx", "src/theme/tokens.css",
                        "src/i18n/locales/ar.json", "package-lock.json"]),
    ("web-react-next", ["app/[locale]/page.tsx", "app/globals.css",
                        "messages/ar.json", "package-lock.json"]),
])
def test_react_fixture_layout(name, files): ...   # files exist; no node_modules committed

def test_react_fixture_gaps_are_lint_findings():
    # lint_generated.py --platform web-react on Card.module.css (vite) → hardcoded-color + physical-direction
    # on Card.tsx (next) → physical-direction

# tests/fixtures/test_web_fixtures.py
@pytest.mark.web
@pytest.mark.parametrize("name", ["web-react-vite", "web-react-next"])
def test_react_fixture_builds(name, tmp_path):
    app = copy_web(name, tmp_path)
    run(app, "npm", "ci", "--no-audit", "--no-fund")
    run(app, "npm", "run", "typecheck")
    run(app, "npm", "run", "build")
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q -k react_fixture` — Expected: FAIL.

- [ ] **Step 3: Create both fixtures** with current stable versions (`npm create vite@latest -- --template react-ts`, `npx create-next-app@latest`), trimmed to the layout above, with the lockfile committed. Components use tokens and i18n correctly except for the deliberate gaps. Keep them small: three components and one screen each.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q -k react_fixture && .venv/bin/pytest -m web tests/fixtures/test_web_fixtures.py -q -k react` — Expected: PASS (web tests need network for `npm ci`).

- [ ] **Step 5: Commit** `git commit -m "feat: web-react Vite and Next fixtures" -- examples/targets/web-react-vite examples/targets/web-react-next tests/skills/test_web_platforms.py tests/fixtures/test_web_fixtures.py`

### Task 6: `web-html` fixture

**Files:**
- Create: `examples/targets/web-html/` with `index.html`, `css/tokens.css`, `css/base.css`, `components/x-button/x-button.{js,css}`, `components/x-card/x-card.{js,css}`, `i18n.js`, `locales/{en,ar}.json`, `icons.svg`, `README.md`. No `package.json`.
- Test: `tests/skills/test_web_platforms.py`, `tests/fixtures/test_web_fixtures.py`

**Interfaces:**
- Produces: `i18n.js` exports `setLocale(lang: string): Promise<void>`. It loads `locales/<lang>.json`, fills `[data-i18n]` and `[data-i18n-attr]`, sets `<html lang dir>` (`dir="rtl"` for `ar`, `he`, `fa`, `ur`), resolves plurals with `Intl.PluralRules` on `key.one`/`key.other`, and reads the initial locale from `?lang=` and then `navigator.language`. The scaffold and build references (Tasks 8, 10) point at this file as the canonical loader. Gap: one `left:` in `x-card.css`.

- [ ] **Step 1: Write the failing tests**:

```python
def test_web_html_fixture_layout():   # files exist, no package.json, gap file lints with physical-direction
    ...

def test_web_html_fixture_is_lint_clean_except_gap():
    # lint_generated.py --platform web-html --allow-colors "css/tokens.css" over every
    # .html/.css/.js file → exactly one finding: physical-direction in components/x-card/x-card.css

@pytest.mark.web
def test_web_html_fixture_loads_in_both_directions(tmp_path):
    # serve the fixture with `python3 -m http.server <free port>` from its root;
    # `npx -y playwright@<pinned> screenshot --viewport-size=390,844 "http://127.0.0.1:<port>/?lang=ar" out.png`
    # → valid PNG; the fixture dir still has no package.json or node_modules afterwards
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q -k web_html_fixture` — Expected: FAIL.

- [ ] **Step 3: Create the fixture** per the interface: custom elements in light DOM, `x-` prefix, module scripts, the source-locale text in the HTML with `data-i18n`.

- [ ] **Step 4: Run** the two default tests, then `.venv/bin/pytest -m web tests/fixtures/test_web_fixtures.py -q -k web_html` — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat: web-html fixture" -- examples/targets/web-html tests/skills/test_web_platforms.py tests/fixtures/test_web_fixtures.py`

### Task 7: Scan references and detection

**Files:**
- Create: `skills/scan-project/references/web-react.md`, `skills/scan-project/references/web-html.md`
- Modify: `skills/scan-project/SKILL.md` (detection table rows, platform order, unsupported list)
- Test: `tests/skills/test_web_platforms.py`

**Interfaces:**
- Consumes: Task 3 enums; Task 5–6 fixtures.
- Produces: profile entries with `platform: web-react|web-html`, `state_management`, `theme.tokens_source`, `localization` (library, catalog paths, `rtl`), and screenshot tooling (Playwright/Storybook) recorded only when runnable. Record the styling system and UI kit in the existing free-form `architecture` evidence; don't add new schema fields.

- [ ] **Step 1: Write the failing tests**:

```python
def test_scan_web_detection_rules():
    skill = (REPO / "skills/scan-project/SKILL.md").read_text()
    assert "| `web-react` |" in skill and "| `web-html` |" in skill
    react = (REPO / "skills/scan-project/references/web-react.md").read_text()
    for needle in ("react-dom", "next", "vite", "App Router", "Pages Router", "@theme",
                   "CSS Modules", "next-intl", "react-i18next", "without executing"):
        assert needle in react
    # Review Focus 1: RN wins over web-react
    assert "react-native" in react and "never `web-react`" in react
    html = (REPO / "skills/scan-project/references/web-html.md").read_text()
    for needle in ("Eleventy", "Astro", "custom elements", "data-i18n", "Django", "Rails",
                   "PHP", "WordPress", "unsupported"):
        assert needle in html

@needs_claude
@pytest.mark.skill
@pytest.mark.parametrize("name,platform", [("web-react-vite", "web-react"),
                                           ("web-react-next", "web-react"),
                                           ("web-html", "web-html")])
def test_scan_profiles_web_fixture(name, platform, tmp_path):
    # run_skill("scan-project") on fixture_copy(name); profile validates;
    # projects[0].platform == platform; localization.rtl is True; theme.tokens_source exists on disk
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q -k scan_web` — Expected: FAIL.

- [ ] **Step 3: Write both references** in the style of `scan-project/references/react-native.md` (imperative bullets), covering design §5.1. Classification rules to state exactly:
  - A runtime `react-native` or `expo` dependency means `react-native`, never `web-react`, even with `react-dom`.
  - Server-template and CMS projects are reported as unsupported with the reason.
  - `web-html` needs at least one `.html` page, or an Eleventy/Astro config, and no React/Vue/Svelte/Angular app entry.
  - A Vue/Svelte/Angular app is reported as unsupported ("next platform").

  Add the table rows and platform order to `SKILL.md` within the word limit.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q -k scan_web`, then the opt-in `-m skill` test for one fixture — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat(scan): web-react and web-html detection" -- skills/scan-project tests/skills/test_web_platforms.py`

### Task 8: Build references

**Files:**
- Create: `skills/build/references/web-react.md`, `skills/build/references/web-html.md`
- Modify: `skills/build/SKILL.md` only if it enumerates platforms (one line; it is over the word budget). Check for Copilot changes first.
- Test: `tests/skills/test_web_platforms.py`

**Interfaces:**
- Consumes: Task 1–2 lint IDs; Task 6 `i18n.js` contract.
- Produces: references with the same section headings as `build/references/react-native.md` (`Tokens, Components, Previews and tests, Strings, Assets, State, Folders, Checks, Don't`), plus `Responsive`, which says how `breakpoints[]` turn into media/container queries.

- [ ] **Step 1: Write the failing test**:

```python
SECTIONS = ["## Tokens", "## Components", "## Responsive", "## Previews and tests", "## Strings",
            "## Assets", "## State", "## Folders", "## Checks", "## Don't"]

@pytest.mark.parametrize("platform,needles", [
    ("web-react", ["'use client'", "server-compatible", "ms-*", "@theme", "next/image",
                   "TODO(sauces)", "--platform web-react", "never invent a translation"]),
    ("web-html", ["light DOM", "data-i18n-attr", "Intl.PluralRules", "<use href",
                  "no build step", "--platform web-html", "Eleventy", "Astro"]),
])
def test_build_reference(platform, needles):
    text = (REPO / f"skills/build/references/{platform}.md").read_text()
    assert [s for s in SECTIONS if s in text] == SECTIONS
    for n in needles: assert n in text
    assert len(text.split()) < 900
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Write both references** from design §5.3 and §5.4. They cover:
  - the anti-goals from design §2;
  - the `--allow-colors` token globs to pass (Tailwind `@theme` file, `tokens.css`, CSS-in-JS theme file);
  - the Checks commands (lockfile package manager; `typecheck`/`tsc --noEmit`; `build`; for `web-html`, the lint `html-parse` pass plus a Playwright load with no console errors).

  Where an API is version-sensitive (Tailwind v3 vs v4, Next Pages vs App Router), name both, as `CLAUDE.md` requires.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/skills/test_web_platforms.py -q -k build_reference` — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat(build): web-react and web-html references" -- skills/build/references/web-react.md skills/build/references/web-html.md tests/skills/test_web_platforms.py`

### Task 9: Verify references and Playwright capture

**Files:**
- Create: `skills/verify/references/web-react.md`, `skills/verify/references/web-html.md`, `skills/verify/references/web-capture.md` (shared: runner choice, seeding order, capture settings, clip rule, browser approval, determinism)
- Modify: `skills/verify/SKILL.md` (one pointer line in §2 and in §6 for the "not designed, not verified" breakpoint wording)
- Test: `tests/skills/test_web_platforms.py`, `tests/fixtures/test_web_fixtures.py`

**Interfaces:**
- Consumes: `screens[].breakpoint`, `sources[].viewport.dpr`; fixtures from Tasks 5–6.
- Produces: per state `.sauces/verify/<screen>@<w>--<state>/iter-<n>/rendered.png` (frame-clipped, scored) and `full.png` (report only); `rtl.png` at the narrowest breakpoint only; summary `renderer` = `"playwright"`.

- [ ] **Step 1: Write the failing tests**:

```python
def test_web_capture_reference():
    text = (REPO / "skills/verify/references/web-capture.md").read_text()
    for needle in ("@playwright/test", "npx -y playwright@", "python3 -m http.server",
                   "deviceScaleFactor", "reducedMotion", "document.fonts.ready",
                   "clip", "full.png", "10%", "Storybook", "manual checklist",
                   "150 MB", "eval-approve", "narrowest", "not designed, not verified",
                   "Tab"):
        assert needle in text
    for p in ("web-react", "web-html"):
        assert "web-capture.md" in (REPO / f"skills/verify/references/{p}.md").read_text()

@pytest.mark.web
def test_capture_matches_frame_size_and_scores(tmp_path):
    # serve examples/designs/login-web/src (or the web-html fixture) with http.server;
    # capture at viewport 1440x900, deviceScaleFactor 1, clip to 1440x900 via a tiny
    # Playwright script written to tmp_path and run with `npx -y playwright@<pinned>` test runner
    # or node; assert PNG size == (1440, 900); run visual_diff.py on it against
    # login@1440--default.png → exit status 0 or 1 with a numeric score on stdout
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Write the references** from design §5.6. The rules that must be in them:
  - Pin the Playwright version once, in `web-capture.md`, and use the same pin in the tests.
  - The seeding preference order, with the per-stack dev-only fixture mechanism: a Next route that returns `notFound()` outside development, an extra Vite HTML entry excluded from `build.rollupOptions.input`, and `web-html` pages under `.sauces/verify/fixtures/`.
  - Never create `package.json` in a `web-html` site that has none.
  - The keyboard check: Tab through each screen and report interactive elements that are unreachable (non-blocking).
  - Verify `SKILL.md` gets one pointer line only.

- [ ] **Step 4: Run** the default tests and `.venv/bin/pytest -m web tests/fixtures/test_web_fixtures.py -q -k capture` — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat(verify): Playwright capture for web platforms" -- skills/verify tests/skills/test_web_platforms.py tests/fixtures/test_web_fixtures.py`

### Task 10: Scaffold (create mode)

**Files:**
- Create: `skills/scaffold/references/web-react.md`, `skills/scaffold/references/web-html.md`
- Modify: `skills/scaffold/SKILL.md` (argument hint, platform words, mapping, ask-list). Check for Copilot changes first.
- Test: `tests/skills/test_web_platforms.py`, `tests/fixtures/test_web_fixtures.py`

**Interfaces:**
- Consumes: Task 6 `i18n.js` (copied as the scaffold's loader), Task 8 Checks.
- Produces: `react|web → web-react → web-app/`, `html → web-html → web-html/`, `--next` modifier. Vite default: React + TS, CSS Modules, `src/theme/tokens.css`, react-i18next with `en` plus the selected locales, Vitest + Testing Library. Playwright is added only through the plan gate at verify time.

- [ ] **Step 1: Write the failing tests**:

```python
def test_scaffold_routes_web():
    skill = (REPO / "skills/scaffold/SKILL.md").read_text()
    for needle in ("`react`", "`html`", "--next", "web-app/", "web-html/"):
        assert needle in skill
    react = (REPO / "skills/scaffold/references/web-react.md").read_text()
    for needle in ("npm create vite@latest web-app", "react-ts", "react-i18next",
                   "create-next-app", "next-intl", "CSS Modules"):
        assert needle in react
    html = (REPO / "skills/scaffold/references/web-html.md").read_text()
    for needle in ("index.html", "css/tokens.css", "i18n.js", "icons.svg", "no build step"):
        assert needle in html

@pytest.mark.web
def test_vite_template_builds(tmp_path):
    run(tmp_path, "npm", "create", "vite@<pinned>", "web-app", "--", "--template", "react-ts")
    run(tmp_path / "web-app", "npm", "install", "--no-audit", "--no-fund")
    run(tmp_path / "web-app", "npm", "run", "build")
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Write both references and the SKILL.md changes** from design §5.7, in the numbered style of `scaffold/references/react-native.md`. Before running any create command, confirm the installed CLI's flags. Add the standard README section and rescan last.

- [ ] **Step 4: Run** the default test and the `-m web` template test — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat(scaffold): web-react and web-html create mode" -- skills/scaffold tests/skills/test_web_platforms.py tests/fixtures/test_web_fixtures.py`

### Task 11: Report breakpoints and eval wiring

**Files:**
- Modify: `skills/report/SKILL.md`, `scripts/eval.py`, `tests/scripts/test_eval.py`. Check for Copilot changes first; eval.py and test_eval.py are the most likely to be dirty.
- Test: `tests/scripts/test_eval.py`, `tests/skills/test_web_platforms.py`

**Interfaces:**
- Consumes: manifest `screens[].breakpoint/base`; summary results by `<screen>@<w>--<state>`.
- Produces in `eval.py`:
  - `SOURCE_EXTENSIONS["web-react"] = {".js", ".jsx", ".ts", ".tsx", ".css", ".scss"}`, `SOURCE_EXTENSIONS["web-html"] = {".html", ".htm", ".css", ".js", ".mjs", ".njk", ".liquid", ".astro"}`. `--create-platform` choices follow automatically.
  - Default builds command when `--builds-cmd` is absent: `web-react` → `npm ci --no-audit --no-fund && npm run build` (plus `npm run typecheck` when the script exists); `web-html` → `python3 -I <repo>/scripts/lint_generated.py --platform web-html <html files>`, where the command passes when no `html-parse` finding exists.
  - Fidelity for web: the minimum default-state score across all breakpoint screens. The table header stays the same.

- [ ] **Step 1: Write the failing tests** in `tests/scripts/test_eval.py` using its existing `make_result` helper pattern, plus:

```python
def test_eval_web_fidelity_is_min_across_breakpoints(tmp_path):
    # result with platform web-react, screens login@390 and login@1440, default scores 95 and 88
    # → fidelity cell "88.0", row FAIL; with 95 and 92 → "92.0", PASS (builds-cmd "true")

def test_eval_web_html_lints_html_and_css(tmp_path):
    # generated index.html with "<h1>Welcome back</h1>" → lint cell "✗ 1"

# tests/skills/test_web_platforms.py
def test_report_has_breakpoints_line():
    text = (REPO / "skills/report/SKILL.md").read_text()
    assert "Breakpoints" in text and "not designed, not verified" in text
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/scripts/test_eval.py tests/skills/test_web_platforms.py -q -k "web or breakpoints"` — Expected: FAIL.

- [ ] **Step 3: Implement** per the interface. In `report/SKILL.md`, add per screen: designed widths, built, verified, and "not designed, not verified" for project breakpoints with no frame. Keep the existing eval output for mobile byte-identical.

- [ ] **Step 4: Run** `.venv/bin/pytest tests/scripts/test_eval.py tests/skills/test_web_platforms.py -q` — Expected: PASS.

- [ ] **Step 5: Commit** `git commit -m "feat: web breakpoints in report and eval" -- skills/report/SKILL.md scripts/eval.py tests/scripts/test_eval.py tests/skills/test_web_platforms.py`

### Task 12: Docs, metadata and the end-to-end exit check

**Files:**
- Modify: `docs/superpowers/spec.md` (§6 platform references list, §7 drop "Web targets" and point to the web design), `docs/superpowers/specs/2026-11-24-sauces-v0.1-design.md` (non-goals line → pointer), `CLAUDE.md` (supported targets table: two web rows), `README.md` (badges, platforms table, scaffold command, requirements: Node + Playwright for web verify, eval commands for the web fixtures), `.claude-plugin/plugin.json` (description mentions web; keywords `react`, `nextjs`, `html`, `css`, `web`), `CHANGELOG.md` if present
- Test: `tests/skills/test_plugin_discovery.py`

- [ ] **Step 1: Write the failing test**:

```python
def test_manifest_mentions_web():
    data = json.loads((REPO / ".claude-plugin/plugin.json").read_text())
    assert {"react", "nextjs", "html", "css", "web"} <= set(data["keywords"])
    assert "web" in data["description"].lower()
    assert "Web targets" not in (REPO / "docs/superpowers/spec.md").read_text().split("## 7.")[1].split("## 8.")[0]
```

- [ ] **Step 2: Run** — Expected: FAIL.

- [ ] **Step 3: Update the docs and metadata** as listed. Keep the README voice: simple and plain (see commit `c76724e`).

- [ ] **Step 4: Exit check.** Run all four; Expected: everything passes.
  - `claude plugin validate .claude-plugin/plugin.json`
  - `.venv/bin/pytest -q`
  - `.venv/bin/pytest -m web -q`
  - The live eval, once per web fixture and once per create platform, each in a fresh results folder:
    - `.venv/bin/python scripts/eval.py --run --fixtures web-react-vite --design examples/designs/login-web` (repeat for `web-react-next` and `web-html`)
    - `--fixtures empty --create-platform web-react` and `--create-platform web-html`

  Every row must PASS (builds, rendered, lint ✓, fidelity ≥ 90 at both breakpoints). Record the table in the eval baseline the README points to. If a row fails, fix the reference that caused it and rerun that row only.

- [ ] **Step 5: Commit and merge** `git commit -m "docs: web targets in README, spec and manifest" -- <paths>`, then push to main.
