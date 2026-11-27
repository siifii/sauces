---
name: cook
description: This skill should be used when the user asks to "cook", "implement this design", "turn this Figma into code", "build these screens from the design", "design to code", or runs "/sauces:cook" with Figma links, PNG/JPG screenshots, PDFs or SVGs. Runs the full Sauces pipeline (ingest, scan, plan, build, verify, report) against the current mobile project, resumes where it stopped, and creates a project first when the folder is empty.
argument-hint: "[--lite] <figma-url | file | folder | glob>..."
---

# Cook

Run the whole pipeline on the design sources in `$ARGUMENTS`: ingest → scan-project → plan → build → verify → report. Each stage is its own skill; cook runs them in order, resumes from the first stage that isn't done, picks the mode, and keeps the user posted.

## Hard rules

- The target root is the current working directory. All state lives in `.sauces/` there.
- Run each stage by invoking its skill (`sauces:ingest`, `sauces:scan-project`, `sauces:scaffold`, `sauces:plan`, `sauces:build`, `sauces:verify`, `sauces:report`) and follow it fully. Never redo a stage's work by hand or skip its checks.
- Plan is the one human checkpoint. Never let build start until `.sauces/plan.json` has `"approved": true`.
- When a stage stops with a problem, stop cook too: print `✗ <stage> (<reason>)`, and say that `/sauces:cook` with the same sources resumes from that stage. Never continue past a failed stage.
- Never skip an unreadable source silently. Name each one at the end with its reason.
- Eval mode (`.sauces/eval-approve` exists): never ask. The stage skills know what to do in eval mode; let them. The file is single-use: delete it as the very last action of this cook run, whether cook finished, found nothing to do or stopped at a failed stage, and never earlier (scan, scaffold, plan, verify and report all read it). When plan ran in eval mode, say "Eval mode: the plan was approved automatically." in the final reply.

## 1. Sources and resume point

0. **Lite run.** If `$ARGUMENTS` contains `--lite`, remove it from the arguments and create `.sauces/lite` (empty). It makes this run cheaper: web screens keep only their narrowest frame, and verify skips the determinism pass, the pseudo-locale pass and all but one fix round. Like `eval-approve`, the file is for this run only: delete it with `rm -f .sauces/lite` as the very last action of this cook run, whatever the outcome, and say "Lite run" in the final reply with what was skipped.
1. Split `$ARGUMENTS` into Figma links (`https://…figma.com/…`) and local paths (files, folders, globs; expand globs; quote paths with spaces). With arguments, write them to `.sauces/cook-sources.json` as a JSON array of strings, exactly as given (only when the file is missing or holds a different list, so an unchanged rerun writes nothing). With no arguments, take the list from `.sauces/cook-sources.json`, so the hash below stays the same; if it is missing, say: "Give me the design: `/sauces:cook <figma-url | file | folder>...`" and stop.
2. Hash the local sources. Missing paths are a usage error: name them and stop.

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" hash <local paths...>
   ```

   With only Figma links, use the hash `figma-only`.
3. Ask for the resume point:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" next --inputs-hash <H>
   ```

   - `done` and no Figma links: say "Nothing to do: the design hasn't changed and every stage is done. Report: `.sauces/report.html`." Stop without running any stage or writing any file (only the eval-mode cleanup above).
   - `done` with Figma links: Figma files can change remotely. Copy `.sauces/manifest.json`, `.sauces/references/` and `.sauces/assets/` to a temporary folder outside `.sauces/`, rerun ingest (section 2, ingest row), then compare (`diff -rq`) the copies with the new files. Identical: say "Nothing to do: the Figma design is unchanged and every stage is done." and stop. Different: run `sauces_state.py reset-from scan` and continue from scan.
   - Any stage name: start there. Say which stage you resume from when it is not `ingest`.

## 2. Run the stages

For each stage from the resume point on, print `▸ <stage>…`, invoke the skill, then print `✓ <stage> (<one-line result>)` and record it with `sauces_state.py mark <stage>` (the build, verify and report skills mark themselves; marking again is harmless).

| Stage | Invoke with | One-line result | Mark |
|---|---|---|---|
| ingest | the sources | screens, states, unreadable count | `mark ingest --inputs-hash <H>` |
| scan | (no args) | mode, platform, architecture | `mark scan` |
| plan | (no args) | items by decision, recommendations, approved by | `mark plan` once approved |
| build | (no args) | files created / changed, TODOs | (marks itself) |
| verify | (no args) | score per default state, passed count | (marks itself) |
| report | (no args) | report path | (marks itself) |

Stage details:

- **After scan**, choose the mode with `${CLAUDE_PLUGIN_ROOT}/skills/cook/references/modes.md`. For create mode, print `▸ scaffold…`, invoke `sauces:scaffold` (it asks for platforms, creates the project and rescans), then `✓ scaffold (<project folder>, <structure>)`. Mark scan only once the mode is settled: right after scan in follow mode, after the user picked a project in ask mode, and only after a successful scaffold and rescan (a completed project is listed and selected if the profile is ambiguous) in create mode. If the user declines, a template handoff is pending, or scaffold refuses, leave scan unmarked and stop, so cook can resume after the user decision or completed template handoff.
- **Plan**:
  - If the resume point is `plan`, no earlier stage ran in this cook, `.sauces/plan.json` already has `"approved": true` (the user approved after the last cook stopped), and `plan.json` is newer than both `manifest.json` and `project-profile.json` (compare modification times; an older plan was made for other inputs), keep it: print `✓ plan (already approved)`, mark it and go on to build.
  - Otherwise run the plan skill. In eval mode it approves itself. Interactively it ends with the approval question: stop and wait for the user's reply, and handle it exactly as the plan skill's approval gate says. Once `approved: true`, mark plan and continue with build in the same conversation. If the user asks for changes, let the plan skill revise and ask again. If the conversation ends first, the next `/sauces:cook` resumes at plan and keeps the plan if it was approved in the meantime.
- **Build** refuses an unapproved plan; that is correct. Don't work around it.
- **Verify**: a state below the threshold is a result, not a failure. Continue to report and say which states fell short.

## 3. Finish

Reply in at most ~150 words:

1. The report: `.sauces/report.html`, plus the report skill's top three audit findings.
2. The mode (follow, create or the picked project) and the one-line result of every stage that ran.
3. Every unreadable source from `.sauces/manifest.json` with its reason (for a Figma link without a Figma MCP server: "connect a Figma MCP server, then run `/sauces:cook` again").
4. The next step: TODOs to resolve (`.sauces/todos.json`), states below the threshold, or "review the diff and commit".

Then, in eval mode, delete `.sauces/eval-approve` (`rm -f .sauces/eval-approve`).
