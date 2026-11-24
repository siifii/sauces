---
name: plan
description: This skill should be used when the user asks to "plan the implementation", "map the design to components", "what can we reuse", "make a component plan", "which design system structure should we use", or runs "/sauces:plan". Maps every design element to reuse / extend / new / token decisions, recommends a design-system structure, turns scan findings into recommendations, lists strings and dependency changes in .sauces/plan.md and plan.json, then stops for user approval.
---

# Plan

Turn `.sauces/manifest.json` (ingest) and `.sauces/project-profile.json` (scan) into `.sauces/plan.md` for people and `.sauces/plan.json` for `build`. This is the single human checkpoint: `build` refuses to run until `plan.json` has `"approved": true`.

## Hard rules

- The target root is the current working directory. Paths in the plan are relative to it, POSIX style.
- Write only `.sauces/plan.json` and `.sauces/plan.md`. Never create, edit, format or move project code, and never run code generators or package managers. The plan describes changes; `build` makes them.
- Never plan to replace, rename, move or delete an existing user component. Reuse it, extend it additively, or wrap it.
- Never add a dependency silently. Every package build would add is a `dependency_changes` entry the user approves.
- Every recommendation offers `keep` and defaults to `choice: "keep"`. New code follows the project either way, and generated code never hard-codes colors or user-facing strings.
- Never write `approved: true` without an explicit yes from the user, except in eval mode (step 9).
- Never invent facts. Values come from the manifest, the profile or files you read. Say "unknown" rather than guess.

## 1. Load inputs

1. Read `.sauces/manifest.json` and `.sauces/project-profile.json`. If either is missing, stop and tell the user to run `/sauces:ingest` and `/sauces:scan-project` (or `/sauces:cook`).
2. Profile `mode`:
   - `existing`: plan for the project in `projects`. With several, plan for the first in platform order (`flutter`, `ios-swiftui`, `android-compose`, `kmp-cmp`) unless the user named one, and say so.
   - `ambiguous`: plan for the project the user picked during scan. In eval mode (`.sauces/eval-approve` exists) take the first in platform order.
   - `empty`: stop. Tell the user to scaffold a project first (`/sauces:scaffold`, or `/sauces:cook` offers it), then rerun scan and plan.
3. Read the platform's build reference, `${CLAUDE_PLUGIN_ROOT}/skills/build/references/<platform>.md`, when it exists. Its sections (`## Tokens` … `## Folders`) describe good code on that platform; items and recommendations must agree with them, and `## Don't` lists what never to plan. Sections that only say "Filled in by the build task." carry no guidance yet. If no reference exists for the platform, plan from the profile alone and say in the summary that detailed platform guidance comes in a later Sauces version.
4. Read the existing components' source files listed in `components[]` (params, variants, defaults), the theme files (`theme.location`, `theme.tokens_source`) and, when `localization.system` is not `none`, the source-locale string file in `localization.location`.

## 2. Choose the structure

Read `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-system-patterns.md` and follow it: decide which patterns are offered, score them, write `structure` (`recommended`, `choice` = `recommended`, 2–4 `reasons`, `options` with folders). Every item gets its `layer` and `path` from that file's level → layer table after the choice is made.

## 3. Map design elements to items

Read `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/matching.md` and follow it. In short:

- Walk every state's `layout` of every screen. Each distinct UI element (component node, or a meaningful group such as a form) becomes one item, with the states it appears in merged into one item. A screen is one `screen`-level item.
- Match each element against `components[]` by kind and parameter fit, score a `confidence`, and decide `reuse` (≥ 0.8), `extend` (0.5–0.8, naming the exact additive param or variant) or `new` (< 0.5).
- Map design tokens to the theme's existing tokens first. Plan `token` items only for additive tokens (new values new components need). A change to an existing theme value is never an item: it becomes a `theme` recommendation (step 5), and with `keep` the items record the expected fidelity difference.
- Map `manifest.assets` (icons, illustrations) to existing assets, the platform's icon set, or a new asset, per `matching.md`.

Every item has: `id` (`item-1`, `item-2`, … in plan order: tokens, assets, atoms, molecules, organisms, screens), `design_ref` (`<screen>/<state>#<element>`, for example `login/default#button`; use the first state where it appears), `decision`, `name`, `path` (the target file for new/token items, the existing file for reuse/extend), `level`, `layer`, `confidence`, `existing_path` for `reuse`/`extend`, and `notes` (states covered, the exact change for `extend`, anything build must know).

Behavior the design does not show (navigation, validation, API calls) is not planned. Note it on the screen item as a `TODO(sauces)` build will leave.

## 4. Strings

List every distinct user-facing text in the design as one `strings[]` entry `{key, value, screen}`:

- `value` is the exact text as shown (`Forgot password?`, keep punctuation and case). Error, empty and loading copy from every state counts.
- Exclude sample content: nodes with `placeholder: true` and field values such as `alex@example.com` or masked passwords, unless the design shows them as hint text the user sees in an empty field.
- Keys are camelCase: feature, then meaning (`loginTitle`, `loginEmailLabel`, `loginSignInButton`, `loginErrorInvalidCredentials`).
- When the source-locale file already has the same text, reuse that key and mark it "existing" in `plan.md`.
- Where the strings go depends on `localization.system`, per `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/recommendations.md` (strings rule). The plan only lists them; build writes them.

## 5. Recommendations

Read `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/recommendations.md`. For each profile finding in an area the new UI touches, write one recommendation: `id` (`rec-<finding id>`, for example `rec-colors-1`), `finding_id`, `title`, `why` (what was found, with paths, and why it matters), `options` (always `keep` first, then the concrete options from the reference with their `changes` and `files`), `choice: "keep"`. Skip a finding only when the new UI never touches its area, and say so in `plan.md`. Also add the theme-change recommendations from that file's section 3 (design differences that only a change to the existing theme would fix) and, when `localization.system` is `none`, the localization recommendation from its strings section.

## 6. Dependency changes

List in `dependency_changes` every package build would add for the plan as it stands (with `keep` choices). Follow the dependency section of `recommendations.md`. An option that needs a package names it in its `changes`; when the user picks that option, add the entry. Flutter golden tests need no package (`flutter_test` ships with the SDK). Leave the list empty when nothing is needed and say "None" in `plan.md`.

## 7. Design suggestions

If `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-review.md` exists, follow it to add design suggestions to the plan. Otherwise skip this step and leave the section out.

## 8. Write and validate

Write `.sauces/plan.json` with `version: 1`, `approved: false`, `approved_by: null`, `platform`, `structure`, `items`, `recommendations`, `strings` and `dependency_changes`. Use only schema fields. Validate:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/check_json.py" "${CLAUDE_PLUGIN_ROOT}/skills/plan/references/plan-schema.json" .sauces/plan.json
```

- Exit 0: valid.
- Exit 1: each `path: message` line is an error. Fix the file and validate again. Repeat until it exits 0. Never stop with an invalid plan.
- Exit 2: schema or usage problem. Check the command and paths, then rerun.

Then write `.sauces/plan.md` with exactly these sections in this order:

1. A title line and a status line (`Status: waiting for approval` or `Status: approved by user|eval`).
2. `## Design-system structure`: the chosen pattern, the reasons, the alternatives with their folders.
3. `## Summary`: screens and states, counts by decision (reuse / extend / new / token), strings count, recommendations count, dependency changes count.
4. `## Components`: a table `ID | Design ref | Decision | Name | Level | Layer | Path | Existing | Confidence | Notes`.
5. `## Tokens`: a table of design tokens → existing token or new `token` item (colors with hex, type styles, spacing, radii).
6. `## Strings`: a table `Key | Value | Screen | Existing key?`.
7. `## Recommendations`: per recommendation its id, finding, why, and each option with changes and files; mark the current choice.
8. `## Dependency changes`: a table, or "None".
9. `## Design suggestions`, only when step 7 produced any.
10. `## Graph`: a fenced `mermaid` block starting `graph LR`, edges screens → components → tokens. Node ids use only letters, digits and `_` (`s_login`, `c_item_3`, `t_primary`); labels go in double quotes and contain no `"`, `#`, `;`, `<` or `>` (write hex as `3D5AFE`).

## 9. The approval gate

**Eval mode** (`.sauces/eval-approve` exists): do not ask. Set `approved: true`, `approved_by: "eval"`, keep every recommendation at `keep` (and every design suggestion at its default), keep `structure.choice` equal to `recommended`, validate again, update the status line in `plan.md`, and say in your output: "Eval mode: plan auto-approved with every recommendation kept and the recommended structure."

**Otherwise** stop and send one message, in this order:

1. **Structure**: the recommended pattern with its reasons, then the alternatives (one line each with their folders).
2. **Components**: a short summary of the table (counts by decision, the extends with their exact change, the new components with their paths).
3. **Recommendations**: each id, one-line finding and its options; say every one defaults to `keep`.
4. **Changes to existing shared code**: every `extend` (the exact change) and every theme change an option would make, each with what else uses it (grep the project for its callers or role usages). Say that with the defaults no existing theme value changes.
5. **Dependency changes**: each package, version, scope and reason, or "None".
6. **Design suggestions**: only when step 7 produced any.
7. End with: "Reply 'approve' (optionally with choices like `rec-colors-1: centralize` or `structure: layered`), or tell me what to change."

Then end your turn. Do not continue to build.

When the user replies:

- **Explicit approval** ("approve", "yes", "looks good, go ahead"), with or without choices: record each choice (`recommendations[].choice` = the option id; `structure.choice`). Accept `rec colors-1` for `rec-colors-1`; an unknown id or option is a question back, not a guess. Add the `dependency_changes` entries a chosen option needs. If the structure changed, do not approve yet: recompute every item's `layer` and `path`, add the move-existing-files recommendation (`design-system-patterns.md` section 5, default `keep`), validate, and send one short confirmation round listing what moved and any package added; approve on the user's yes. Otherwise set `approved: true`, `approved_by: "user"`, validate, update `plan.md`, and confirm in one short message: what was chosen, every package a chosen option adds (say explicitly that it will be added), and the next step `/sauces:build`.
- **Change request**: revise items, strings or choices as asked, keep `approved: false`, validate, rewrite `plan.md`, and send the approval message again with the changes highlighted.
- **Anything else** (a question, an unclear reply): answer it and ask again. Never read silence, a question or "ok?" as approval.

Rerunning `/sauces:plan` rewrites the plan and needs a fresh approval.
