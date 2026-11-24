---
name: verify
description: This skill should be used when the user asks to "verify the UI", "compare against the design", "check visual fidelity", "screenshot diff", "does it match the mockup", or runs "/sauces:verify". Renders built screens, diffs them against the reference images, scores fidelity 0–100 and runs a fix loop.
---

# Verify

Render each built screen or component to PNG with the project's own tooling (screenshot tests or previews), then score it against its reference in `.sauces/references/` with `${CLAUDE_PLUGIN_ROOT}/scripts/visual_diff.py`. Save `rendered.png`, `diff.png` and `score.json` per iteration in `.sauces/verify/<screen>/`. When a score is under the threshold (default 90), have the `fidelity-checker` agent explain the differences, apply the fixes, and re-score, for at most 3 iterations per screen. If rendering isn't possible, fall back to a manual checklist and say so plainly. (Stub: implemented in Phase 6.)
