---
name: verify
description: This skill should be used when the user asks to "verify the UI", "compare against the design", "check visual fidelity", "screenshot diff", "does it match the mockup", or runs "/sauces:verify". Renders every built screen state, scores it 0–100 against its design reference, runs a fix loop of at most 3 iterations with the fidelity-checker agent, checks a right-to-left render, and writes .sauces/verify/summary.json.
---

# Verify

Render each built screen state with the project's own test tooling, score it against its reference image, and fix real differences until it reaches the threshold or the iterations run out. Report honestly what still differs and why.

## Hard rules

- The target root is the current working directory. Paths in `.sauces/` files are relative to it.
- The threshold is `fidelity_threshold` from `.sauces/config.json` when that file sets it to a number in 0–100; otherwise 90. Nothing else changes it: not `$ARGUMENTS`, not a caller, not you. Never write `config.json`, never edit a reference image, and never change `visual_diff.py` or a `score.json` to pass.
- At most 3 iterations (renders) per screen. Then record the result and move on.
- Fixes follow the build skill's rules: tokens and l10n only (no hard-coded colors or strings), additive extends, never overwrite or delete a user file, no new packages.
- Never "fix" an intentional deviation (`.sauces/deviations.json`) back to the design, and never hard-code placeholder content, fonts or anti-aliasing artifacts to raise a score.
- Working files go in `.sauces/verify/` only. The render test under `test/sauces/` (or the platform's equivalent) is the one project file verify creates.
- Eval mode (`.sauces/eval-approve` exists): never ask; decide, and say what you decided in the summary.

## 1. Load

1. Set the threshold. Read `.sauces/config.json` if it exists: a number `fidelity_threshold` in 0–100 is the threshold (`threshold_source: "config"`). A missing file or key means 90 (`"default"`). An invalid value (not a number, outside 0–100, unreadable JSON) means 90: say so in one line. If `$ARGUMENTS` asks for another threshold, don't use it; say once that the threshold is set only by `fidelity_threshold` in `.sauces/config.json`, and continue.
2. Read `.sauces/state.json`. If `stages.build.status` is not `done`, say: "Nothing is built yet. Run `/sauces:build` first (or `/sauces:cook`)." and stop.
3. Read `.sauces/plan.json` (`platform`, the `screen`-level items, item `notes`, recommendations), `.sauces/project-profile.json` (the same project selected by build using platform and project_root, with its localization and screenshot tooling), `.sauces/manifest.json` (screens, states, references) and `.sauces/deviations.json` (missing means `[]`).
4. Read the render reference: `${CLAUDE_PLUGIN_ROOT}/skills/verify/references/<platform>.md`. It is binding. If it doesn't exist, rendering isn't supported for this platform yet: go to section 6 (manual checklist).
5. List the states to verify: every manifest state of every screen the plan has a `screen` item for, with id `<screen>--<state>` and its `reference`. Check each reference file exists; a missing one is `rendered: false` with the reason.
6. Delete any previous `.sauces/verify/` contents (it is all Sauces output) so iteration numbers start at 1. Leave `deviations.json` and everything else in `.sauces/` alone.

## 2. Write the render test

Follow the reference's render test section (web platforms: also `${CLAUDE_PLUGIN_ROOT}/skills/verify/references/web-capture.md`): use an existing capture harness where possible, or one test file per screen that renders every state from section 1.5 by seeding the screen's state, plus an RTL pass per state. Read the screen, its state class and the project's test helpers first, so the seeding uses the real API.

- If a render test from an earlier verify exists and `state.json` lists it in `generated_files`, update it in place. If a file at that path exists and isn't listed, it is the user's: pick a free name (`<screen>_sauces_render_test.dart`) and say so.
- Lint and analyze the test as the reference says, and fix every finding.
- Record any new test file: `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" add-files generated <test file>`.

## 3. Render, score, fix (per screen)

For each screen, set `n = 1` and loop:

1. **Render** with the reference's run command for this screen's test file only, into `.sauces/verify/_render/a/`. On iteration 1, run it a second time into `.sauces/verify/_render/b/` (the determinism check). Handle failures as the reference says. If iteration 1 can't render at all, mark the screen's states `rendered: false` and continue with the next screen. If a later render fails, the last fixes broke the build: revert them (only files Sauces changed, `git diff` shows them), re-render once into `_render/a/` without counting an iteration, and stop the loop with the previous iteration's results.
2. **Score** each state. Copy `_render/a/<id>.png` to `.sauces/verify/<id>/iter-<n>/rendered.png`, then:

   ```bash
   python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/visual_diff.py" \
     ".sauces/verify/<id>/iter-<n>/rendered.png" "<state reference>" \
     --out-dir ".sauces/verify/<id>/iter-<n>" --threshold <threshold>
   ```

   It prints the score and writes `diff.png` and `score.json` beside the render. Exit 0 = passed, 1 = under the threshold, 2/3 = usage or missing dependency (fix the command, or tell the user to `python3 -m pip install pillow numpy` and stop). Every state of the screen is scored every iteration, so a fix that breaks another state shows up.

   On iteration 1, also score `_render/b/<id>.png` with `--out-dir ".sauces/verify/_render/b-score/<id>"`. If the two scores of a state differ by more than 0.5, set its `nondeterministic: true`, apply the reference's determinism fix (fixed pump durations, never `pumpAndSettle`), say so, and re-render and re-score iteration 1 (still `n = 1`). Every other state gets `nondeterministic: false`.
3. **Revert regressions.** If a state that passed in iteration `n - 1` is below the threshold now, revert the fixes from iteration `n - 1` that touched the code it renders (only files Sauces changed), re-render once without counting an iteration, and score that render into `iter-<n>` again, replacing the regressed result. Note the revert in that state's `remaining`. Don't re-apply a reverted fix.
4. **Stop** when every state passed, when `n == 3`, or when the last fixes raised no failing state's score by at least 1 point (no progress). Otherwise continue.
5. **Explain.** Dispatch the `fidelity-checker` agent once for the screen with: each failing state's `rendered.png`, reference, `diff.png` and `score.json`; the screen's source files and the components it uses; the state's deviations (suggestion id, region, note: "intended, don't fix"); and the plan item `notes` (kept theme differences, icon substitutions). It returns a list of differences, each either a fix (file, location, change) or "leave" with a reason.
6. **Fix.** Apply each proposed fix you agree with, following `${CLAUDE_PLUGIN_ROOT}/skills/build/references/<platform>.md`. Reject a fix that would hard-code a value, change a kept theme role, undo a deviation or rewrite a user component, and move it to `remaining` with the reason. If no fix is left, stop the loop: the remaining differences are expected.
7. **Check** the files you changed exactly like the build skill's "Check and fix" section (lint, gen-l10n, analyze, the project's tests). Record new files with `add-files generated` and edited ones with `add-files changed`.
8. `n = n + 1` and go back to step 1.

The state's result is its last iteration folder, `iter-<k>` with `k` the last `n` scored: `score` and `passed` from that `score.json` (after any revert in step 3, it reflects the code now in the project), `iterations = k`, `scores` = every iteration's score in order. Collect `remaining` from the fidelity-checker's "leave" items and your rejected fixes, one sentence each (for example "Field values are placeholder content", "Surface is the kept seeded theme tint, not #FFFFFF (plan item 4 notes)").

## 4. RTL

Copy each `_render/a/<id>--rtl.png` from the screen's final render to `.sauces/verify/<id>/rtl.png`. The render test writes the PNG before it fails on an RTL overflow, so the file should exist; if it doesn't, add the rtl_issue "RTL render not produced: <reason from the test output>". Add each line of `_render/a/<id>--rtl.errors.txt` (overflows and exceptions collected during the RTL pump) as an issue. Then run the reference's RTL check and write each issue as one sentence in that state's `rtl_issues` (empty list when clean). RTL issues are reported, not fixed by verify; report lists them for a human. A layout overflow that also occurs in LTR is a build bug and was handled in section 3.

Delete `.sauces/verify/_render/` when all screens are done.

## 5. Summary file

Write `.sauces/verify/summary.json`:

```json
{
  "version": 1,
  "platform": "flutter",
  "threshold": 90,
  "threshold_source": "default",
  "renderer": "flutter test (test/sauces/login_render_test.dart)",
  "results": [
    {"id": "login--default", "screen": "login", "state": "default",
     "reference": ".sauces/references/login--default.png", "rendered": true,
     "score": 93.4, "passed": true, "iterations": 2, "scores": [86.1, 93.4],
     "nondeterministic": false, "rtl_issues": [], "deviations": [],
     "remaining": ["Field values are placeholder content"]}
  ]
}
```

- `deviations`: the `suggestion_id`s in `deviations.json` whose `screen` and `state` match.
- `threshold` and `threshold_source` from section 1.1. `nondeterministic` from section 3.2.
- Not rendered: `rendered: false`, `score: null`, `passed: false`, `iterations: 0`, `scores: []`, `nondeterministic: false`, the reason as the first `remaining` entry.
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

Say plainly that these states were not verified visually and why. Never give them a score. On web, plan breakpoints with no design frame are listed as "not designed, not verified", not as checklist states.

## 7. Record and report

Mark the stage only after the summary validates:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/sauces_state.py" mark verify
```

End with a short message:

- A table: state, score (or "not rendered"), passed, iterations.
- The threshold and where it came from (default or `.sauces/config.json`).
- The fixes applied, with files, and anything reverted. Any state marked nondeterministic.
- What still differs and why (the `remaining` items), the intentional deviations, and RTL issues.
- The fallback, if used: which states and why; the checklist path.
- A tip to add `.sauces/verify/` to `.gitignore` if it isn't there (don't edit it yourself).
- Next step: `/sauces:report`.
