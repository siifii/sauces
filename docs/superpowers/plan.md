# Sauces: build plan (vibe-code in phases)

Work one phase per Claude Code session (or `/clear` between phases). Paste the prompt, review the diff, check the exit criteria, commit, then move on.

---

## Phase 0: Scaffold and validate
**Prompt**
> Read CLAUDE.md and docs/superpowers/spec.md. Scaffold the full plugin structure from spec §6: empty-but-valid SKILL.md files for cook, ingest, scan-project, plan, build, verify, report (proper frontmatter with trigger phrases, one-paragraph body), the three agent files with `<example>` blocks, and stub scripts with argparse `--help`. Update README.md. Then run `claude plugin validate` and fix any errors.

**Exit:** validate passes, `/sauces:` skills appear after a local install.

---

## Phase 1: Test fixtures first
**Prompt**
> Create `examples/`. In `examples/targets/`, make four minimal but realistic sample apps, each with a small theme and 2–3 existing components (a button, a text field, a card): `android-compose/` (Hilt + MVVM, Material 3), `ios-swiftui/` (SPM, MVVM), `kmp-cmp/` (commonMain UI), `flutter-bloc/` (feature-first, BLoC). They only need to be structurally realistic, not to build. In `examples/designs/login/`, add a description.md of a login screen (default + error + loading states). I'll drop real PNG/PDF/SVG exports next to it.

**Exit:** four fixture repos exist. You've added real design exports to `examples/designs/`.

---

## Phase 2: Scan project
**Prompt**
> Implement the scan-project skill per spec §4.2. Put detection heuristics for each platform in `skills/scan-project/references/<platform>.md`. Output must match a JSON schema you define in `skills/scan-project/references/profile-schema.json`. Run it against all four fixtures in examples/targets and show me the four profiles.

**Exit:** each profile correctly names the toolkit, architecture, theme location and existing components.

---

## Phase 3: Ingest
**Prompt**
> Implement the ingest skill (spec §4.1) and the design-analyst agent. Write `scripts/extract_palette.py` (k-means on Pillow + numpy; outputs hex colors with coverage %, and merges near-duplicates with ΔE < 3) and `scripts/rasterize_pdf.py` (pdftoppm if present, otherwise a clear error). Define a manifest schema in `skills/ingest/references/manifest-schema.json`. Handle Figma URLs through the Figma MCP tools if connected; otherwise report that it isn't connected. Test on examples/designs/login.

**Exit:** `.sauces/manifest.json` lists the screens, states, tokens and reference PNGs for the login sample.

---

## Phase 4: Plan
**Prompt**
> Implement the plan skill (spec §4.3). Inputs: manifest.json + project-profile.json. Output plan.md (tables + a mermaid graph of screens → components → tokens) and plan.json with reuse/extend/new/token decisions and confidence. The skill must stop and ask for approval, then record `"approved": true`. Test the login sample against each fixture.

**Exit:** the plan reuses the fixtures' existing button and text field rather than creating new ones.

---

## Phase 5: Build (platform by platform)
Do this four times, once per platform, starting with your strongest.
**Prompt**
> Implement the build skill and the component-builder agent for **{Flutter | Android Compose | iOS SwiftUI | KMP/CMP}**. Put platform rules in `skills/build/references/{platform}.md`: token/theme mapping, component patterns, previews, string resources + RTL, state-management wiring stubs, folder placement, and a short "don't" list. Build order per spec §4.4. Run it on the login sample in the matching fixture and show me the diff.

**Exit:** generated code follows the fixture's conventions, has no hard-coded colors or strings, every component has a preview, and unknown behavior is marked `TODO(sauces)`.

---

## Phase 6: Verify loop
**Prompt**
> Implement `scripts/visual_diff.py`: resize to match, compute pixel diff % and SSIM (numpy implementation), write diff.png as a heatmap and score.json, and output a combined 0–100 score. Then implement the verify skill and the fidelity-checker agent. Add per-platform render instructions to `skills/verify/references/` (Roborazzi/Paparazzi, swift-snapshot-testing, Flutter goldens, CMP desktop screenshot). Max 3 fix iterations, threshold configurable (default 90).

**Exit:** on at least one platform, verify renders, scores, fixes and re-scores automatically.

---

## Phase 7: Report
**Prompt**
> Implement the report skill and `scripts/report_render.py`, which fills `skills/report/assets/report-template.html` from manifest, profile, plan and verify outputs. The page must be self-contained (inline CSS; mermaid via a CDN script tag is fine) and include all sections in spec §4.6, including the design audit: near-duplicate colors, spacing inconsistencies, missing states, WCAG AA contrast and RTL risks. Make it look like a polished case study, not a log dump.

**Exit:** report.html opens offline (except the mermaid graph) and you'd be happy to show it to a client.

---

## Phase 8: Cook (orchestrator) and polish
**Prompt**
> Implement the cook skill that runs the whole pipeline end to end, with an approval gate after plan and clear progress output. Add an eval script `scripts/eval.py` that runs cook on every fixture × design sample and prints a table of fidelity score, reuse decisions, compile/lint flags. Update README with install, usage and a GIF placeholder.

**Exit:** one command produces code + report for every fixture, and the eval table is your baseline.

---

## Later (v0.2+)
- Code Connect auto-suggestions (write mappings back to Figma)
- Storybook/Widgetbook/Showkase catalog generation
- Dark mode and dynamic type / font scale checks
- Publish to a plugin marketplace repo
