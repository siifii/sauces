# Sauces 🥫

> We make the sauce; you make the sandwich.

A Claude Code plugin that turns design sources (Figma, PNG, PDF, SVG) into production UI that fits your existing mobile project (Android Compose, iOS SwiftUI, KMP/CMP, Flutter), checks it visually, and gives you a report.

**Status:** pre-alpha. Phase 0 (scaffold) is done: the skills, agents and scripts exist as stubs. See `docs/superpowers/spec.md` and `docs/superpowers/plan.md`.

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

| Command | What it does |
|---|---|
| `/sauces:cook <sources…>` | Full pipeline: ingest → scan → plan → build → verify → report |
| `/sauces:ingest <sources…>` | Normalize design sources into `.sauces/manifest.json` |
| `/sauces:scan-project` | Detect platform, architecture, tokens and components → `.sauces/project-profile.json` |
| `/sauces:plan` | Map design → code (reuse / extend / new / token). Stops for your approval |
| `/sauces:build` | Implement the approved plan in your project's conventions |
| `/sauces:verify` | Render, diff against the design, fix loop |
| `/sauces:report` | Self-contained `.sauces/report.html` |

All working state lives in `.sauces/` in your project. Consider adding `.sauces/verify/` to your `.gitignore`.

## Layout
```
.claude-plugin/   plugin.json, marketplace.json (local dev)
.mcp.json         Figma MCP server
skills/           cook, ingest, scan-project, plan, build, verify, report
agents/           design-analyst, component-builder, fidelity-checker
scripts/          extract_palette, visual_diff, rasterize_pdf, report_render (Python 3, Pillow + numpy)
docs/superpowers/ spec and build plan
```

## Requirements
- Python 3 with Pillow and numpy (scripts run with `python3 -I`)
- `pdftoppm` (poppler) for PDF inputs
- Figma MCP connected for Figma links
