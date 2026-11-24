# Sauces: product spec (v0.1)

## 1. Problem

Mobile teams receive designs as a messy mix: a Figma link (sometimes well structured, often not), exported PNGs, a PDF of the flow, loose SVG icons. Turning that into UI that fits an *existing* codebase (its theme, components, state management, folder layout) is slow, repetitive work. Existing tools (Figma MCP, Builder.io Visual Copilot, Locofy, Anima, screenshot-to-code) mostly assume a clean Figma file and a web/React target, and they don't audit the design or explain what they did.

## 2. Positioning

Sauces is a mobile-first, repo-aware design-implementation agent. It differs from existing tools in five ways:

1. **Mixed inputs.** Figma, PNG/JPG, PDF and SVG together, grouped into screens and states.
2. **Fits the repo.** Reuses existing components and tokens, follows the detected architecture, and only creates what's missing.
3. **All four mobile stacks.** Android Compose, iOS SwiftUI, KMP/CMP and Flutter, treated equally.
4. **Checks itself.** Renders previews or screenshot tests, diffs them against the design and iterates.
5. **Report.** A component graph, reuse stats, a design audit (inconsistencies, missing states) and best practices.

Sauces uses the official Figma MCP server when a Figma link is given. It does not reimplement Figma parsing.

## 3. Users and entry points

The user is a mobile developer or lead working in Claude Code inside their app repo.

| Command (skill) | Does |
|---|---|
| `/sauces:cook <sources…>` | Full pipeline: ingest → scan → plan → build → verify → report |
| `/sauces:ingest <sources…>` | Normalize design sources into `.sauces/manifest.json` |
| `/sauces:scan-project` | Detect platform and architecture, inventory components and tokens → `.sauces/project-profile.json` |
| `/sauces:plan` | Map design → code (reuse / extend / new) → `.sauces/plan.md` + `plan.json`. **Stops for user approval.** |
| `/sauces:build` | Implement the approved plan, tokens first, then atoms → molecules → screens |
| `/sauces:verify` | Render, visual diff, fix loop → `.sauces/verify/` |
| `/sauces:report` | Generate `.sauces/report.html` (graph + audit + best practices) |

Sources can be Figma URLs, file paths, folders or globs. Anything Sauces can't read (for example a Figma link with no MCP connected) is reported clearly, never skipped silently.

## 4. Pipeline

```
sources ─► INGEST ─► manifest.json
repo    ─► SCAN   ─► project-profile.json
            both  ─► PLAN ─► plan.md / plan.json ──(user approves)──►
                     BUILD ─► code in repo + previews/tests
                     VERIFY ─► diffs, scores, fix loop (max N iterations)
                     REPORT ─► report.html
```

### 4.1 Ingest
- **Figma:** call the Figma MCP tools (`get_design_context`, `get_variable_defs`, `get_screenshot`, `get_metadata`). Save a reference screenshot for each frame.
- **PNG/JPG:** use as-is as reference images. Have the `design-analyst` agent describe the layout tree, text, colors, spacing and components.
- **PDF:** rasterize each page (`pdftoppm` if present, else Pillow/pdf fallback) and treat it like an image. Extract embedded text where possible.
- **SVG:** classify as icon or illustration. Icons become vector assets (Android VectorDrawable / ImageVector, iOS asset catalog / SF Symbol match suggestion, Flutter `flutter_svg` or icon font).
- **Grouping:** cluster inputs into screens, and screens into states (default, loading, empty, error, dark mode) by filename and visual similarity. Ask when unsure.
- **Tokens:** extract a palette (`scripts/extract_palette.py`), type scale, spacing scale and radii. Merge in Figma variables when available.

### 4.2 Scan project
Detect:
- Platform(s) and UI toolkit (from `build.gradle(.kts)`, `Package.swift` / `.xcodeproj`, `pubspec.yaml`, KMP source sets)
- Architecture and state management (ViewModel/MVI, TCA, BLoC/Riverpod…)
- Theme / design-system location and existing tokens
- Component inventory: name, path, params/props, preview availability
- Conventions: folder structure, naming, string resources/localization (including RTL support), DI, navigation
- Screenshot test tooling available (Paparazzi/Roborazzi, swift-snapshot-testing, Flutter golden tests) or what to add

### 4.3 Plan
For each design element, decide one of:
- `reuse`: an existing component matches (record confidence)
- `extend`: an existing component needs a new variant or param
- `new`: create it, at the right atomic level (atom / molecule / organism / screen)
- `token`: a new or changed design token

The output is a human-readable `plan.md` (tables + mermaid graph) and a machine `plan.json`. Sauces **must stop here** and get the user's approval before writing code.

### 4.4 Build
Order: tokens/theme → icons/assets → atoms → molecules → organisms → screens. Each component gets a preview (Compose `@Preview`, SwiftUI `#Preview`, Flutter widgetbook-style example or golden test) and uses string resources, never hard-coded text. Behavior that isn't visible in the design (navigation, validation, API calls) becomes `TODO(sauces): …` comments plus a list in the report. Never guess it.

### 4.5 Verify
Render each screen or component to PNG with the project's tooling, then run `scripts/visual_diff.py` against the reference. Score from 0 to 100 (pixel + structural similarity), plus a heatmap. Under the threshold (default 90), the `fidelity-checker` agent explains the differences and the builder fixes them. Max 3 iterations per screen. If rendering isn't possible, fall back to a manual checklist and say so.

### 4.6 Report
`report.html` is self-contained and works offline:
- Summary: screens built, components reused / extended / new, fidelity scores
- Mermaid graph: screens → components → tokens
- Design audit: near-duplicate colors (ΔE < 3), inconsistent spacing, divergent button/text styles, missing states, contrast failures (WCAG AA), RTL risks
- TODOs that need a human
- Best practices applied and recommended next steps for this platform

## 5. Working state (`.sauces/` in the target repo)

```
.sauces/
  manifest.json          sources, screens, states, tokens
  references/            normalized reference PNGs (one per screen/state)
  project-profile.json   scan output
  plan.md / plan.json    mapping plan (approved flag)
  verify/<screen>/       rendered.png, diff.png, score.json per iteration
  report.html
```

Suggest adding `.sauces/verify/` to `.gitignore`.

## 6. Components of the plugin

- **Skills:** cook, ingest, scan-project, plan, build, verify, report
- **Agents:** `design-analyst` (image → structured layout spec), `component-builder` (one component, one platform), `fidelity-checker` (explains diffs, proposes fixes)
- **Scripts:** `extract_palette.py`, `visual_diff.py`, `rasterize_pdf.py`, `report_render.py` (fills the HTML template from JSON)
- **MCP:** Figma (official, HTTP)
- **Platform references:** `android-compose.md`, `ios-swiftui.md`, `kmp-cmp.md`, `flutter.md`, shared by build/verify/scan

## 7. Non-goals for v0.1
- Web targets
- Backend/API wiring
- Writing back to Figma
- Animations beyond simple state transitions

## 8. Success metrics (evals)
- Fidelity score ≥ 90 on the sample set for each platform
- Reuse precision: % of `reuse` decisions a human agrees with
- Zero hard-coded strings or colors in generated code (lint check)
- Build compiles on first try for ≥ 80% of components
