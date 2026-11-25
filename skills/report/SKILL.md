---
name: report
description: This skill should be used when the user asks to "generate the report", "show the design audit", "summarize what was built", "component graph", "reuse stats", or runs "/sauces:report". Produces a self-contained .sauces/report.html with a component graph, reuse stats, fidelity scores, localization status, the design audit, TODOs, best practices and next steps.
---

# Report

Render `.sauces/report.html` from the working state, then tell the user where it is and what matters most. The script does the work; do not hand-write HTML or recompute audit facts.

## Hard rules

- The target root is the current working directory. Read only from `.sauces/`; write only `.sauces/report.html`.
- Never edit any `.sauces/` input to make the report look better. If a stage hasn't run, its section says "not run" — that is correct output.
- Report numbers exactly as the files give them. Never invent scores, counts or findings in the chat summary.
- Eval mode (`.sauces/eval-approve` exists): never ask; just render and summarize.

## 1. Check

If `.sauces/manifest.json` doesn't exist, say: "Nothing to report yet. Run `/sauces:ingest` (or `/sauces:cook`) first." and stop. Any other missing file is fine.

## 2. Render

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/report_render.py" --sauces-dir .sauces
```

- Exit 0: the report is at `.sauces/report.html`.
- Exit 3 (missing Pillow/numpy): show the install command from the error and stop.
- Any other failure: show the error output verbatim and stop. Do not write a report by hand.

Then record it:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" mark report
```

## 3. Summarize in chat

Read `.sauces/design-audit.json`, `.sauces/verify/summary.json` and `.sauces/todos.json` (skip any that are missing) and reply in at most ~120 words:

1. The path: `.sauces/report.html` (say it is self-contained and opens in any browser; the graph needs internet for mermaid, with a text fallback).
2. One line of headline numbers: screens built, fidelity per state (or "verify not run"), TODO count.
3. **The three most important audit findings**, one line each with the guideline it cites. Rank by severity (`high` > `medium` > `low` > `info`), then accessibility before consistency before everything else, then by order in the file. Mention a finding's linked design suggestion and its keep/apply decision if `plan.json` has one. If there are fewer than three findings, list what exists; if there is no audit, say so.
4. The first next step: an unresolved TODO, an unreadable source, or a state below threshold, whichever comes first.
