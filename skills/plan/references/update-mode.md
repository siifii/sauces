# Update mode

Update mode runs when `.sauces/design-diff.json` exists: the design changed since the last run. Without it (first run, no snapshot, or `--full`) ignore this file.

## Inputs

- `.sauces/design-diff.json` (validate with `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-diff-schema.json`).
- `.sauces/previous/plan.json`: the plan the project was last built from.

## Plan

- Plan items only for states with status `changed` or `added`, and for changed or added tokens, copy and assets.
- Carry over every item of the previous plan whose `design_ref` belongs to an `unchanged` state, unchanged: same `id`, `decision`, `path`, with `"update": "unchanged"`. Item ids of new items continue after the highest previous id.
- A changed element that maps to a component used by unchanged screens stays additive (`extend`, never a breaking change). Put those screens' state ids in the item's `affects`.
- Removed states: never delete anything. Add one `recommendation` (default `keep`) listing the generated files that served only that state and saying they were left in place.
- Copy changes: a changed string whose key is in the previous plan's `strings[]` gets a new `value` for that key. A key that is not in the previous plan's `strings[]` belongs to the user: plan a new key and a `TODO(sauces)` for the old one, never an edit.
- Write `plan.json` `update`: `{from_plan, changed, added, removed, unchanged}` (state ids) and begin `plan.md` with one line saying the plan is an update and how many states changed.
- The approval gate is unchanged.

## Build

Skip items with `"update": "unchanged"`. Apply the rest as usual. Do not rewrite files of unchanged screens, even when the formatter would change them.

## Verify

Verify every state, changed or not: a shared component that changed can regress an unchanged screen, so re-verification of unchanged states catches regressions from `extend` changes. `--full` and first runs skip update mode entirely.
