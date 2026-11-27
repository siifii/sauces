<div align="center">

<img src="assets/icon.png" alt="Sauces" width="120" height="120" />

# Sauces

Give it a design. Get mobile or web UI that fits your app.

*We make the sauce; you make the sandwich.*

[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=claude&logoColor=white)](https://code.claude.com/docs/en/plugins)
[![Version](https://img.shields.io/badge/version-0.1.0-orange)](.claude-plugin/plugin.json)
[![Status](https://img.shields.io/badge/status-alpha-yellow)](#status)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

[![Flutter](https://img.shields.io/badge/Flutter-02569B?logo=flutter&logoColor=white)](#what-it-works-with)
[![Jetpack Compose](https://img.shields.io/badge/Jetpack_Compose-4285F4?logo=jetpackcompose&logoColor=white)](#what-it-works-with)
[![SwiftUI](https://img.shields.io/badge/SwiftUI-F05138?logo=swift&logoColor=white)](#what-it-works-with)
[![Compose Multiplatform](https://img.shields.io/badge/Compose_Multiplatform-7F52FF?logo=kotlin&logoColor=white)](#what-it-works-with)
[![React Native](https://img.shields.io/badge/React_Native-20232A?logo=react&logoColor=61DAFB)](#what-it-works-with)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](#what-it-works-with)
[![Next.js](https://img.shields.io/badge/Next.js-000000?logo=nextdotjs&logoColor=white)](#what-it-works-with)
[![HTML/CSS](https://img.shields.io/badge/HTML%2FCSS-E34F26?logo=html5&logoColor=white)](#what-it-works-with)

</div>

---

Sauces is a plugin for [Claude Code](https://code.claude.com). You give it a design (a Figma link, screenshots, a PDF or some SVG icons) and it builds that screen inside your mobile app or website.

It reads your project before writing anything, so the new code uses your architecture, your theme, your components and your translation files. Then it renders every screen state, compares it to the design, fixes what doesn't match, and writes you a report.

## Install

Run these two lines inside Claude Code:

```text
/plugin marketplace add siifii/sauces
/plugin install sauces@sauces
```

You also need Python 3 with Pillow and numpy:

```bash
python3 -m pip install pillow numpy
```

## Use it

Open Claude Code in your app's folder and run:

```text
/sauces:cook ./designs/login.png ./designs/login-error.png
```

You can mix sources in one go: `https://figma.com/design/...`, `./designs/*.png`, `./flow.pdf`.

Sauces pauses once to show you the plan. Nothing gets written until you approve it. If you stop halfway, run the same command again and it picks up where it left off. If nothing changed, it does nothing.

## What happens when you run it

```text
ingest → scan → plan → (you approve) → build → verify → report
```

1. **Ingest** reads your design files.
2. **Scan** looks at your project: platform, architecture, theme, components, languages.
3. **Plan** decides, for each piece of the design, whether to reuse an existing component, extend one, make a new one, or turn it into a token (a color, a spacing value, a font).
4. **Build** writes the code the way your project already does things.
5. **Verify** renders each state with your project's own test tools and scores it 0 to 100 against the design. Below the threshold, it fixes and tries again, up to 3 times.
6. **Report** writes `.sauces/report.html`, a single file you can open or share.

It also picks a mode based on your folder:

| Your folder has | Sauces will |
|---|---|
| An app it supports (at the root or in a subfolder) | Follow your existing patterns. If it spots a best-practice gap, it suggests a fix, but the default is to leave your code as it is. |
| Nothing yet (just a README, docs, dotfiles or designs) | Offer to create a new project with the platform's official tools, then build into it. |
| Several apps, or one it can't figure out | Ask you which one to use. It won't guess. |

## Why it's useful

Most design-to-code tools expect a tidy Figma file and a brand new app. Most teams have an existing codebase and a designer who sent PNGs. Sauces is made for that case.

- It never quietly overwrites your components. It reuses them, adds optional parameters, or asks you first.
- Every piece of text goes into your translation files, in every language you have. Existing keys get reused, and right-to-left layouts are rendered and checked too. Icons become real project assets.
- It audits the design for things like low contrast, tap targets that are too small and colors that are almost the same, and says which guideline each finding comes from. You decide which ones to fix.
- Anything it can't read gets reported. It never skips a file without telling you.

## Commands

`cook` runs everything. Each step also has its own command if you only want that part:

| Command | What it does |
|---|---|
| `/sauces:cook <sources…>` | The whole thing, start to finish |
| `/sauces:ingest <sources…>` | Read the designs into `.sauces/manifest.json` |
| `/sauces:scan-project` | Study your project into `.sauces/project-profile.json` |
| `/sauces:scaffold [flutter\|android\|ios\|kmp\|react-native\|react\|html]` | Create a new project in an empty folder |
| `/sauces:plan` | Make the plan and wait for your OK |
| `/sauces:build` | Write the code from the approved plan |
| `/sauces:verify` | Render, score and fix (3 rounds max) |
| `/sauces:report` | Write `.sauces/report.html` |

## What it works with

| Platform | UI | Architectures it recognizes | How it checks the result | Scaffold name |
|---|---|---|---|---|
| Flutter | Widgets | BLoC/Cubit, Riverpod, Provider, feature-first folders | Flutter widget rendering | `flutter` |
| Android | Jetpack Compose | MVVM/MVI, Hilt/Koin, Material 3 | Screenshot runner or instrumentation | `android` |
| iOS | SwiftUI | MVVM/TCA, SPM modules | Snapshot runner or Xcode UI tests | `ios` |
| Compose Multiplatform | Compose in `commonMain` | Shared vs platform UI, expect/actual | Capture from a mobile host | `kmp` |
| React Native | Expo or bare | Expo Router, React Navigation, hooks, Zustand, Redux Toolkit | Maestro, Detox or device capture | `react-native` |
| Web: React (`web-react`) | Next.js (App or Pages Router) or Vite | Tailwind, CSS Modules, CSS-in-JS, next-intl, react-i18next | Playwright in Chromium, at every designed width | `react` |
| Web: HTML (`web-html`) | Plain HTML/CSS/JS, Eleventy, Astro | Custom elements, CSS custom-property tokens, `data-i18n` | Playwright in Chromium, at every designed width | `html` |

Android XML Views and UIKit are recognized but not supported, and Sauces tells you so. For React Native, `/sauces:scaffold react-native` uses Expo; add `--bare` for the Community CLI. Both put the app in `react-native-app/`.

For the web, `/sauces:scaffold react` creates a Vite + React + TypeScript app in `web-app/` (add `--next` for Next.js), and `/sauces:scaffold html` creates a static site with no build step in `web-html/`. Web designs often come at several widths (a phone frame and a desktop frame): Sauces builds one responsive screen and checks it at each width you designed. Widths you didn't design are listed as "not designed, not verified". Vue, Svelte, Angular, Django/Rails/PHP templates and WordPress are recognized but not supported yet.

You'll need the usual tools for your platform:

- Flutter needs the Flutter SDK.
- Android Compose needs the Android SDK, a JDK and the project's Gradle wrapper.
- SwiftUI needs Xcode on a Mac with an iOS simulator installed.
- Compose Multiplatform needs the Android and iOS toolchains for each host you want to build.
- React Native needs Node.js and your package manager, plus the native toolchains for native builds.
- Web needs Node.js. Verify uses Playwright with Chromium (about 150 MB the first time); Sauces asks before installing it, and a plain HTML site gets no `package.json`.
- PDF designs need `pdftoppm` (`brew install poppler` or `apt install poppler-utils`).

If Sauces can't render on your machine, verify gives you a checklist to go through by hand instead of a score.

## Figma (optional)

You only need this for Figma links. Sauces doesn't come with a Figma connection and won't add one for you. If you want it, add the official Figma server yourself:

```bash
claude mcp add --transport http figma https://mcp.figma.com/mcp
```

or connect the Figma connector on claude.ai. Without it, Figma links show up as "unreadable" in the summary and report, and screenshots, PDFs and SVGs still work fine.

## Settings

Sauces keeps all its files in a `.sauces/` folder inside your project. To change how strict verify is, put this in `.sauces/config.json`:

```json
{ "fidelity_threshold": 95 }
```

The default is 90. You'll probably want to add `.sauces/verify/` (the rendered screenshots) to your `.gitignore`.

## Privacy

Sauces runs inside your Claude Code session. It doesn't bundle any MCP server and doesn't send your code or designs anywhere on its own. Figma data only goes through a Figma server that you connected. When it scaffolds a new project, it uses the platform's official tools (like `flutter create` or `create-expo-app`), and those may download templates and packages.

## Status

This is an alpha (v0.1). All seven platforms have scan, scaffold, build and verify, and Flutter has had the most use. The web platforms are the newest. Full end-to-end runs on the native platforms haven't been validated yet, so expect some rough edges. If something breaks, please [open an issue](https://github.com/siifii/sauces/issues).

Sauces isn't in the Claude plugin directory. Install it from this repo with the two commands above.

## FAQ

**Will it overwrite my components?**
No. It reuses them, extends them with optional parameters, or wraps them, and asks when none of that works. You see every decision in the plan before any code is written.

**Do I need Figma?**
No. Screenshots, PDFs and SVGs work on their own.

**My project doesn't follow best practices. Is that a problem?**
No. Sauces follows what you already have. Anything it would do differently shows up as a suggestion, and the default is "keep as is".

**Can I run just one step?**
Yes. Every step has its own command, and `cook` resumes from the last step that finished.

## Development

<details>
<summary>Repo layout, tests and evals</summary>

```text
.claude-plugin/   plugin.json, marketplace.json
assets/           plugin icon
skills/           cook, ingest, scan-project, scaffold, plan, build, verify, report
agents/           design-analyst, component-builder, fidelity-checker
scripts/          Python 3 helpers (Pillow + numpy), including eval.py
examples/         sample designs and target projects
docs/superpowers/ spec and build plans
```

```bash
python3 -m venv .venv && .venv/bin/pip install pillow numpy pytest
.venv/bin/python -m pytest -q            # default tests
.venv/bin/python -m pytest -m skill -v   # headless claude runs (slow, uses tokens)
claude plugin validate .
claude --plugin-dir .                    # try your local copy
```

**Evals** score full `cook` runs on the fixtures in `examples/targets/`:

```bash
.venv/bin/python scripts/eval.py --run --fixtures flutter-bloc,empty --out eval.md
```

`--run` copies each fixture to a temp folder, writes `.sauces/eval-approve` there so the plan is approved automatically (cook deletes the file when it's done), and calls `claude` once per fixture. That costs tokens, needs a network connection, and results change from run to run. No passing baseline has been recorded yet. Without `--run`, `eval.py --results <dir>` scores runs you already have. A row passes when the project builds, every state rendered, the generated code passes lint, and the default state scores at least 90. With `--run`, cook also has to exit successfully.

The default tests include a Flutter render check when Flutter and the fixture's dependencies are installed. Run `flutter pub get` in `examples/targets/flutter-bloc` to turn it on.

**Mobile checks.** The SDK-backed suite builds the fixtures and fresh starters for Android Compose, SwiftUI and Compose Multiplatform. It also type-checks and bundles Expo for both platforms, and checks that the bare React Native template creates both native hosts. To capture on a test device that's already booted (and reserved for this run), set `SAUCES_ANDROID_SERIAL` or `SAUCES_IOS_SIMULATOR`.

```bash
.venv/bin/pytest -m mobile
```

The live evaluator starts a fresh Claude Code pipeline. Run it once for each existing fixture, then once per platform with `--fixtures empty --create-platform <platform-id>`, using a new results folder each time. Add `--bare` to the React Native create run to test the Community CLI template. `--require-captures` requires passing, deterministic captures for every state, plus clean RTL captures when the profile says the app supports RTL.

```bash
.venv/bin/python scripts/eval.py --run --fixtures android-compose \
  --results /tmp/sauces-android-follow --builds-cmd './gradlew assembleDebug' --require-captures
.venv/bin/python scripts/eval.py --run --fixtures empty --create-platform react-native \
  --results /tmp/sauces-expo-create --builds-cmd 'npx expo export --platform android --platform ios' \
  --require-captures
```

**Web checks.** The `web` suite installs and builds the React fixtures (`web-react-vite`, `web-react-next`), loads the `web-html` fixture in Chromium in both directions, and checks the capture script verify uses. It needs Node and a network connection for `npm ci`.

```bash
.venv/bin/pytest -m web
.venv/bin/python scripts/eval.py --run --fixtures web-react-vite --design examples/designs/login-web \
  --results /tmp/sauces-web-vite
.venv/bin/python scripts/eval.py --run --fixtures empty --create-platform web-html \
  --design examples/designs/login-web --results /tmp/sauces-web-html-create
```

Fixture results show that the sample code builds or renders. Live results show whether Sauces can scaffold or change it and match the design. A live run needs Claude usage credits, the platform SDKs and a working device or screenshot runner.

</details>

## Contributing

Issues and pull requests are welcome. Before you start, read [`docs/superpowers/spec.md`](docs/superpowers/spec.md) and [`docs/superpowers/plan.md`](docs/superpowers/plan.md). Skills are written as instructions for Claude, so keep them that way. Run the tests and `claude plugin validate .` before you open a PR.

## License

[MIT](LICENSE) © 2026 Kareem Alsaifi
