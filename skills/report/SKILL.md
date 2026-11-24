---
name: report
description: This skill should be used when the user asks to "generate the report", "show the design audit", "summarize what was built", "component graph", "reuse stats", or runs "/sauces:report". Produces a self-contained .sauces/report.html with a component graph, reuse stats, fidelity scores, design audit, TODOs and best practices.
---

# Report

Collect `.sauces/manifest.json`, `project-profile.json`, `plan.json` and the `verify/` results, and render a self-contained `.sauces/report.html` with `${CLAUDE_PLUGIN_ROOT}/scripts/report_render.py`. Include a summary (screens built, components reused/extended/new, fidelity scores), a mermaid graph of screens → components → tokens, the design audit (near-duplicate colors, spacing inconsistencies, divergent styles, missing states, WCAG AA contrast, RTL risks), the TODOs that need a human, and best practices plus next steps for the detected platform. (Stub: implemented in Phase 7.)
