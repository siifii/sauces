---
name: verify
description: This skill should be used when the user asks to "verify the UI", "compare against the design", "check visual fidelity", "screenshot diff", "does it match the mockup", or runs "/sauces:verify". Renders every built screen state, scores it 0–100 against its design reference, runs a fix loop of at most 3 iterations with the fidelity-checker agent, checks a right-to-left render, and writes .sauces/verify/summary.json.
argument-hint: [--threshold <0-100>]
---

# Verify

Render each built screen state with the project's own test tooling, score it against its reference image, and fix real differences until it reaches the threshold or the iterations run out. Report honestly what still differs and why.

## Hard rules

- The target root is the current working directory. Paths in `.sauces/` files are relative to it.
- The threshold is 90 unless `$ARGUMENTS` contains `--threshold <n>` (0–100). Never lower it on your own, never edit a reference image, and never change `visual_diff.py` or a `score.json` to pass.
- At most 3 iterations (renders) per screen. Then record the result and move on.
- Fixes follow the build skill's rules: tokens and l10n only (no hard-coded colors or strings), additive extends, never overwrite or delete a user file, no new packages.
- Never "fix" an intentional deviation (`.sauces/deviations.json`) back to the design, and never hard-code placeholder content, fonts or anti-aliasing artifacts to raise a score.
- Working files go in `.sauces/verify/` only. The render test under `test/sauces/` (or the platform's equivalent) is the one project file verify creates.
- Eval mode (`.sauces/eval-approve` exists): never ask; decide, and say what you decided in the summary.

## 1. Load

1. Parse `$ARGUMENTS` for `--threshold`. Reject a value outside 0–100 with a one-line usage message and stop.
2. Read `.sauces/state.json`. If `stages.build.status` is not `done`, say: "Nothing is built yet. Run `/sauces:build` first (or `/sauces:cook`)." and stop.
3. Read `.sauces/plan.json` (`platform`, the `screen`-level items, item `notes`, recommendations), `.sauces/project-profile.json` (the project for that platform, its `root`, `localization`, `screenshot_tooling`), `.sauces/manifest.json` (screens, states, references) and `.sauces/deviations.json` (missing means `[]`).
4. Read the render reference: `${CLAUDE_PLUGIN_ROOT}/skills/verify/references/<platform>.md`. It is binding. If it doesn't exist, rendering isn't supported for this platform yet: go to section 6 (manual checklist).
5. List the states to verify: every manifest state of every screen the plan has a `screen` item for, with id `<screen>--<state>` and its `reference`. Check each reference file exists; a missing one is `rendered: false` with the reason.
6. Delete any previous `.sauces/verify/` contents (it is all Sauces output) so iteration numbers start at 1. Leave `deviations.json` and everything else in `.sauces/` alone.

## 2. Write the render test

Follow the reference's render test section: one test file per screen that pumps every state from section 1.5 by seeding the screen's state, plus an RTL pass per state. Read the screen, its state class and the project's test helpers first, so the seeding uses the real API.

- If a render test from an earlier verify exists and `state.json` lists it in `generated_files`, update it in place. If a file at that path exists and isn't listed, it is the user's: pick a free name (`<screen>_sauces_render_test.dart`) and say so.
- Lint and analyze the test as the reference says, and fix every finding.
- Record it: `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" add-files generated <test file>`.

## 3. Render, score, fix (per screen)

For each screen, set `n = 1` and loop:

1. **Render** with the reference's run command into `.sauces/verify/_render/`. Handle failures as the reference says. If the screen can't be rendered at all, mark its states `rendered: false` and continue with the next screen.
2. **Score** each state. Copy `_render/<id>.png` to `.sauces/verify/<id>/iter-<n>/rendered.png`, then:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/visual_diff.py" \
     ".sauces/verify/<id>/iter-<n>/rendered.png" "<state reference>" \
     --out-dir ".sauces/verify/<id>/iter-<n>" --threshold <threshold>
   ```

   It prints the score and writes `diff.png` and `score.json` beside the render. Exit 0 = passed, 1 = under the threshold, 2/3 = usage or missing dependency (fix the command, or tell the user to `python3 -m pip install pillow numpy` and stop). Every state of the screen is scored every iteration, so a fix that breaks another state shows up.
3. **Stop** when every state passed, when `n == 3`, or when the last fixes raised no failing state's score by at least 1 point (no progress). Otherwise continue.
4. **Explain.** Dispatch the `fidelity-checker` agent once for the screen with: each failing state's `rendered.png`, reference, `diff.png` and `score.json`; the screen's source files and the components it uses; the state's deviations (suggestion id, region, note: "intended, don't fix"); and the plan item `notes` (kept theme differences, icon substitutions). It returns a list of differences, each either a fix (file, location, change) or "leave" with a reason.
5. **Fix.** Apply each proposed fix you agree with, following `${CLAUDE_PLUGIN_ROOT}/skills/build/references/<platform>.md`. Reject a fix that would hard-code a value, change a kept theme role, undo a deviation or rewrite a user component, and move it to `remaining` with the reason. If no fix is left, stop the loop: the remaining differences are expected.
6. **Check** the files you changed exactly like the build skill's "Check and fix" section (lint, gen-l10n, analyze, the project's tests). Record new files with `add-files generated` and edited ones with `add-files changed`.
7. **Revert regressions.** After the next render, if a state that had passed dropped below the threshold, undo the fix that caused it (`git diff` shows it) and keep the earlier iteration's result for the loop's outcome.
8. `n = n + 1` and go back to step 1.

The state's result is its last iteration: `score` and `passed` from that `score.json`, `iterations = n`, `scores` = every iteration's score in order. Collect `remaining` from the fidelity-checker's "leave" items and your rejected fixes, one sentence each (for example "Field values are placeholder content", "Surface is the kept seeded theme tint, not #FFFFFF (plan item 4 notes)").

## 4. RTL

Copy each `_render/<id>--rtl.png` from the screen's final render to `.sauces/verify/<id>/rtl.png`. Then run the reference's RTL check and write each issue as one sentence in that state's `rtl_issues` (empty list when clean). RTL issues are reported, not fixed by verify; report lists them for a human. A layout overflow that also occurs in LTR is a build bug and was handled in section 3.

Delete `.sauces/verify/_render/` when all screens are done.

## 5. Summary file

Write `.sauces/verify/summary.json`:

```json
{
  "version": 1,
  "platform": "flutter",
  "threshold": 90,
  "renderer": "flutter test (test/sauces/login_render_test.dart)",
  "results": [
    {"id": "login--default", "screen": "login", "state": "default",
     "reference": ".sauces/references/login--default.png", "rendered": true,
     "score": 93.4, "passed": true, "iterations": 2, "scores": [86.1, 93.4],
     "rtl_issues": [], "deviations": [],
     "remaining": ["Field values are placeholder content"]}
  ]
}
```

- `deviations`: the `suggestion_id`s in `deviations.json` whose `screen` and `state` match.
- Not rendered: `rendered: false`, `score: null`, `passed: false`, `iterations: 0`, `scores: []`, the reason as the first `remaining` entry.
- One result per state from section 1.5, in manifest order.

Validate it and fix any error:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/check_json.py" "${CLAUDE_PLUGIN_ROOT}/skills/verify/references/summary-schema.json" .sauces/verify/summary.json
```

## 6. Manual checklist (fallback)

When any state has `rendered: false`, write `.sauces/verify/checklist.md`: one section per such state with its reference path, why it couldn't be rendered, and checkboxes a person can tick while comparing the running app with the reference:

- Every text matches the copy in the manifest exactly, and comes from the string resources.
- Colors match the manifest tokens (name each with its hex).
- Spacing, sizes and corner radii (list the measured values from the manifest layout).
- The state shows what the reference shows (error text, loading indicator, disabled button).
- Right-to-left: the layout mirrors, and nothing clips or overflows.

Say plainly that these states were not verified visually and why. Never give them a score.

## 7. Record and report

Mark the stage only after the summary validates:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" mark verify
```

End with a short message:

- A table: state, score (or "not rendered"), passed, iterations.
- The fixes applied, with files, and anything reverted.
- What still differs and why (the `remaining` items), the intentional deviations, and RTL issues.
- The fallback, if used: which states and why; the checklist path.
- A tip to add `.sauces/verify/` to `.gitignore` if it isn't there (don't edit it yourself).
- Next step: `/sauces:report`.
