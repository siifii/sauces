# Sauces — Claude Code plugin

> We make the sauce; you make the sandwich.

Sauces is a **Claude Code plugin** that takes design sources (Figma links, PNG/JPG screenshots, PDFs, SVGs), reads the target mobile or web project, and implements the UI as reusable components that follow *that project's* architecture and conventions. It verifies the result visually and finishes with a report: a component graph, reuse stats, a design audit and best practices.

## What this repo is

This repo IS the plugin. There's no app code here. The deliverables are markdown skills, agent definitions, small Python helper scripts and JSON config, laid out in the Claude Code plugin format:

```
.claude-plugin/plugin.json     manifest (name: sauces)
skills/<skill>/SKILL.md        one folder per skill, details in references/
agents/<agent>.md              subagents (frontmatter: name, description w/ <example>, model, color, tools)
scripts/                       Python 3 helpers (Pillow, numpy only, no heavy deps)
examples/                      sample design inputs + sample target projects for testing
tests/                         pytest suite (default, -m web, -m mobile, -m skill)
```

## Supported targets

| Platform | UI toolkit | Architecture to detect & follow |
|---|---|---|
| Android | Jetpack Compose (primary), XML Views (read-only awareness) | MVVM / MVI, Hilt/Koin, Material 3 |
| iOS | SwiftUI (primary), UIKit (awareness) | MVVM / TCA, SPM modules |
| KMP / CMP | Compose Multiplatform in `commonMain` | shared UI vs platform-specific, expect/actual |
| Flutter | Widgets | BLoC/Cubit, Riverpod, Provider; feature-first folders |
| React Native | Expo or bare | Expo Router / React Navigation, hooks, Zustand, Redux Toolkit |
| Web (React) | React 19: Next.js (App/Pages Router) or Vite | Tailwind v3/v4, CSS Modules, CSS-in-JS; next-intl, react-i18next; Vitest + Testing Library |
| Web (HTML) | Static HTML/CSS/JS, Eleventy, Astro | custom elements in light DOM, CSS custom-property tokens, `data-i18n` loader |

## Rules for writing this plugin

- Skills are instructions FOR Claude. Write them as imperative directives ("Scan the project…"), not docs for humans.
- SKILL.md body stays under ~2,000 words. Platform-specific detail goes in `skills/<skill>/references/<platform>.md`.
- Frontmatter `description` is third person and lists the trigger phrases in quotes.
- Refer to plugin files with `${CLAUDE_PLUGIN_ROOT}/...`. Never use absolute paths.
- All working state goes in a `.sauces/` folder inside the user's target project. Never scatter files.
- Never overwrite an existing user component silently. Extend it, wrap it, or ask.
- Scripts must run with `python3 -I` and only Pillow + numpy. Each one needs a `--help`.
- Keep platform knowledge correct and current. If unsure about an API, say so in the reference file rather than inventing one.

## How to test

- `claude plugin validate .claude-plugin/plugin.json`
- Install locally: `/plugin marketplace add ./` then `/plugin install sauces` (or `claude --plugin-dir .`).
- Run the pipeline against the sample projects in `examples/targets/` with the inputs in `examples/designs/`.
- `.venv/bin/pytest -q` (default suite) must pass before every commit; run `-m web` / `-m mobile` when you touch those platforms.
