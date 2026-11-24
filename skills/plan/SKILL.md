---
name: plan
description: This skill should be used when the user asks to "plan the implementation", "map the design to components", "what can we reuse", "make a component plan", or runs "/sauces:plan". Maps each design element to reuse / extend / new / token decisions in .sauces/plan.md and plan.json, then stops for user approval.
---

# Plan

Read `.sauces/manifest.json` and `.sauces/project-profile.json`, then decide for each design element whether to `reuse` an existing component (with a confidence), `extend` one with a new variant or param, create a `new` one at the right atomic level, or add/change a `token`. Write a human-readable `.sauces/plan.md` (tables plus a mermaid graph of screens → components → tokens) and a machine-readable `.sauces/plan.json`. Stop and ask the user to approve the plan; only after explicit approval set `"approved": true` in `plan.json`. Never write project code from this skill. (Stub: implemented in Phase 4.)
