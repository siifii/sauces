---
name: cook
description: This skill should be used when the user asks to "cook", "implement this design", "turn this Figma into code", "build these screens from the design", "design to code", or runs "/sauces:cook" with Figma links, PNG/JPG screenshots, PDFs or SVGs. Runs the full Sauces pipeline (ingest, scan, plan, build, verify, report) against the current mobile project.
argument-hint: <figma-url | file | folder | glob>...
---

# Cook

Run the full Sauces pipeline on the sources in `$ARGUMENTS`, in order: ingest → scan-project → plan → build → verify → report. Keep all working state in `.sauces/` at the target project root. Stop after plan and wait for the user's explicit approval before writing any code. Print a one-line progress update as each stage starts and finishes, and report any source that couldn't be read instead of skipping it. (Stub: the orchestration is implemented in Phase 8; for now, tell the user which stage skills exist and that cook isn't wired up yet.)
