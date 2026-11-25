# Sauces 🥫

> We make the sauce; you make the sandwich.

A Claude Code plugin that turns design sources (Figma, PNG, PDF, SVG) into UI that fits your mobile project's conventions, checks it visually, and gives you a report.

**Status:** alpha. Sauces has scan, scaffold, build, and verification workflows for the five targets below. Live end-to-end runs on native targets still need validation.

| Target | Scaffold argument | Visual verification |
|---|---|---|
| Flutter for Android and iOS | `flutter` | Flutter widget rendering |
| Android with Jetpack Compose | `android` | Screenshot runner or Android instrumentation |
| iOS with SwiftUI | `ios` | Snapshot runner or Xcode UI tests |
| Compose Multiplatform for Android and iOS | `kmp` | Capture from a configured mobile host |
| React Native for Android and iOS (Expo or bare) | `react-native` | Maestro, Detox, or scripted device capture |

Use `/sauces:scaffold react-native` for Expo or add `--bare` for the React Native Community CLI. Both create the app in `react-native-app/`.

Android Compose, SwiftUI, and Compose Multiplatform use bundled starters by default. Selecting a different IDE template can require a handoff. Visual scoring requires a compatible runner and uses the manual checklist when rendering is unavailable. Android XML Views and UIKit are detected as unsupported targets.

## Install (local dev)
```bash
claude --plugin-dir /path/to/sauces
```
Or from inside Claude Code:
```
/plugin marketplace add ./
/plugin install sauces@sauces-dev
```

## Usage
```
/sauces:cook https://figma.com/design/... ./designs/*.png ./flow.pdf
```

`cook` runs every stage, prints `▸ stage…` / `✓ stage (result)` as it goes, and stops once for your approval of the plan. Run it again with the same sources and it resumes where it stopped; with nothing changed it does nothing.

| Command | What it does |
|---|---|
| `/sauces:cook <sources…>` | Full pipeline: ingest → scan → plan → build → verify → report |
| `/sauces:ingest <sources…>` | Normalize design sources into `.sauces/manifest.json` |
| `/sauces:scan-project` | Detect platform, architecture, tokens and components → `.sauces/project-profile.json` |
| `/sauces:scaffold [flutter\|ios\|android\|kmp\|react-native]` | Create a new project in an empty folder (create mode) |
| `/sauces:plan` | Map design → code (reuse / extend / new / token). Stops for your approval |
| `/sauces:build` | Implement the approved plan in your project's conventions |
| `/sauces:verify` | Render every state, score it against the design, fix loop (max 3) |
| `/sauces:report` | Self-contained `.sauces/report.html` |

The verification threshold defaults to 90. To change it, set `fidelity_threshold` to a number from 0 to 100 in your target project's `.sauces/config.json`, for example `{"fidelity_threshold": 95}`.

### Modes

| Your folder | Mode | What happens |
|---|---|---|
| A supported app project (at the root or in a child folder) | **follow** | New UI follows your architecture, state management, theme and folders. Best-practice gaps become optional recommendations (default: keep as is). |
| Empty (only README, docs, licences, dotfiles or design files) | **create** | Sauces offers to scaffold a project with the selected platform’s official tooling, then builds into it. |
| Several projects, or one Sauces can't classify | **ask** | Sauces asks which project to target. It never guesses. |

### Highlights

- **Reuse first.** Every design element maps to reuse / extend / new / token. Existing components are extended with optional parameters, never silently overwritten.
- **Localization & resources.** Every user-facing string goes to your localization files in every locale (existing keys are reused), right-to-left layouts are rendered and checked, and icons become project assets. The report shows keys added and reused per locale, what still needs translating, and RTL issues.
- **Design audit.** Measured accessibility and consistency findings (contrast, touch targets, near-duplicate colors…) with the guideline each one cites. You decide per suggestion whether to keep the design or apply the fix.
- **Visual verification.** Each state is rendered with your project's own test tooling and scored 0–100 against the design.

All working state lives in `.sauces/` in your project. Consider adding `.sauces/verify/` to your `.gitignore`.

## Layout
```
.claude-plugin/   plugin.json, marketplace.json (local dev)
.mcp.json         Figma MCP server
skills/           cook, ingest, scan-project, scaffold, plan, build, verify, report
agents/           design-analyst, component-builder, fidelity-checker
scripts/          Python 3 helpers (Pillow + numpy), including eval.py
docs/superpowers/ spec and build plans
```

## Requirements
- Python 3 with Pillow and numpy: `python3 -m pip install pillow numpy` (scripts run with `python3 -I`)
- Node.js and the app’s package manager for React Native. Native builds also use the relevant Android or iOS toolchain.
- Flutter SDK for Flutter projects
- Android SDK, a compatible JDK, and the project’s Gradle wrapper for Android Compose
- Xcode on macOS with an installed iOS simulator for SwiftUI
- The applicable Android and iOS toolchains for each Compose Multiplatform host you want to build or render
- `pdftoppm` (poppler) for PDF inputs: `brew install poppler` / `apt install poppler-utils`
- A Figma MCP server for Figma links: the plugin's own (`.mcp.json`) or a connected claude.ai Figma connector. Without one, Figma links are reported as unreadable, never skipped silently.

## Development
```bash
python3 -m venv .venv && .venv/bin/pip install pillow numpy pytest
.venv/bin/python -m pytest -q            # default tests
.venv/bin/python -m pytest -m skill -v   # headless claude runs (slow, uses tokens)
claude plugin validate .
```

Evals score full `cook` runs on the fixtures in `examples/targets/`:
```bash
.venv/bin/python scripts/eval.py --run --fixtures flutter-bloc,empty --out eval.md
```
The default tests include a Flutter render-template check when Flutter and the fixture's resolved dependencies are available. Run `flutter pub get` in `examples/targets/flutter-bloc` to enable it.

`--run` copies each fixture to a temp folder, writes `.sauces/eval-approve` there (the plan is approved automatically, and cook deletes the file when it finishes) and calls `claude` once per fixture: it costs tokens, needs network, and results vary between runs. The command above writes the baseline to `eval.md`; no passing baseline has been recorded yet. Without `--run`, `eval.py --results <dir>` scores existing runs. A row passes when the project builds, every state rendered, the generated code passes lint, and the default state scores ≥ 90. With `--run`, cook must also exit successfully.


## Mobile parity checks

The SDK-backed suite builds both existing fixtures and fresh bundled starters for Android Compose, SwiftUI, and Compose Multiplatform. It also type-checks and bundles Expo for both mobile platforms, and checks that the bare React Native template generates both native hosts. Set `SAUCES_ANDROID_SERIAL` or `SAUCES_IOS_SIMULATOR` to capture the Compose and SwiftUI fixtures on an already booted test device. Use an Android or iOS test device reserved for the run.

```bash
.venv/bin/pytest -m mobile
```

The live evaluator starts a fresh Claude Code pipeline. Run it once per existing fixture, then once per platform with `--fixtures empty --create-platform <platform-id>`. Use a fresh results directory for each run. Add `--bare` to the React Native create run to exercise the Community CLI template. `--require-captures` requires passing, deterministic captures for every state and clean RTL captures when the profile declares RTL support.

```bash
.venv/bin/python scripts/eval.py --run --fixtures android-compose \
  --results /tmp/sauces-android-follow --builds-cmd './gradlew assembleDebug' --require-captures
.venv/bin/python scripts/eval.py --run --fixtures empty --create-platform react-native \
  --results /tmp/sauces-expo-create --builds-cmd 'npx expo export --platform android --platform ios' \
  --require-captures
```

Fixture results establish that the sample code builds or renders. Live results establish whether Sauces can scaffold or modify it and reproduce the original design. A live run needs Claude usage credits, platform SDKs, and a working device or screenshot runner.
