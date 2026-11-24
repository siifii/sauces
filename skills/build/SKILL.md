---
name: build
description: This skill should be used when the user asks to "build the approved plan", "implement the components", "generate the UI code", "write the screens", or runs "/sauces:build". Implements an approved .sauces/plan.json in the project's own architecture: tokens first, then atoms, molecules, organisms and screens.
---

# Build

Refuse to start unless `.sauces/plan.json` has `"approved": true`. Implement the plan in this order: tokens/theme → icons/assets → atoms → molecules → organisms → screens, following the conventions recorded in `.sauces/project-profile.json`. Give every component a preview, use string resources instead of hard-coded text, and use theme tokens instead of hard-coded colors. Mark behavior the design doesn't show (navigation, validation, API calls) with `TODO(sauces): …` comments instead of guessing it. Never overwrite an existing user component silently: extend it, wrap it, or ask. Delegate single components to the `component-builder` agent. (Stub: implemented in Phase 5.)
