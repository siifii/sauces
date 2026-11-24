# Design-system signals

Record the evidence `plan` needs to recommend how components are organized (atomic, layered, feature-first or follow the project; see `${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-system-patterns.md`). Ingest only records facts. It never picks a pattern.

Write the result as the manifest's optional `design_system` object:

```json
"design_system": {
  "signals": [{"kind": "repetition", "detail": "text-field appears 6 times in login (default, error, loading)", "evidence": "login--default, login--error, login--loading"}],
  "component_candidates": [{"name": "text-field", "occurrences": 6, "screens": ["login"], "variants": ["outlined", "error"]}]
}
```

Write `design_system` whenever at least one state has a `layout` or a Figma source was read. Both lists are required inside it; use `[]` when one is empty.

## 1. Component candidates (every source)

Compute these after step 5 (Analyze), from the `layout` of every state of every screen:

1. Walk every layout tree depth first and collect each node with `type: "component"`. Skip `component.kind` values that are not reusable UI: `system-bar` (device chrome) and `divider`/`image` only when they are decoration with no variant.
2. Group by `component.kind`. The candidate `name` is the kind exactly as the analysis reported it (`text-field`, `button`, `link`, `icon-button`). When a Figma component name is known for that kind (section 2), use the Figma name instead, in kebab-case (`Input/Text` → `input-text`), and keep one candidate per Figma component.
3. `occurrences`: count every node of that kind across all states of all screens. States count separately: the same field in the default, error and loading states is three occurrences. Two fields of the same kind in one state are two occurrences. Example: a login screen with an email and a password field in three states gives `text-field` × 6 and its single button gives `button` × 3.
4. `screens`: the distinct screen ids where the kind appears, in manifest order.
5. `variants`: the distinct `component.variant` values seen for that kind, in first-seen order (`filled`, `loading`, …). `[]` when none was reported.
6. Order candidates by `occurrences` descending, then by name.

Count only what the layouts contain. Never add a candidate from `description.md` or from what a screen "probably" has.

## 2. Signals

Each signal is `{kind, detail, evidence?}`. `detail` is one plain sentence with the numbers. `evidence` is a short pointer to where you saw it: a Figma node or page name, a variable collection name, or reference names.

| kind | Record it when | Source |
|---|---|---|
| `repetition` | a component kind occurs ≥ 2 times in total, or appears on ≥ 2 screens | layouts (images, PDFs, Figma frames) |
| `figma-naming` | Figma pages, frames, sections or components are named with design-system terms (`Atoms`, `Molecules`, `Organisms`, `Templates`, `Foundations`, `Tokens`, `Components`, `Patterns`) | Figma `get_metadata` |
| `component-set` | the file defines component sets with variants; one signal per set, with its variant count | Figma `get_metadata` / `get_design_context` |
| `variables` | the file uses variables; say how many collections and whether they are tiered (primitive → semantic) | Figma `get_variable_defs` |
| `library` | frames use components from a published library | Figma library tools, if available |

How to read the Figma-only kinds is in `${CLAUDE_PLUGIN_ROOT}/skills/ingest/references/figma.md` §5.

For `repetition`, write one signal per candidate that qualifies, plus one summary signal with the totals, for example `"5 distinct component kinds across 1 screen and 3 states"` (evidence: the screen ids). `plan` scores from these numbers.

## 3. Never fabricate

- Figma signals (`figma-naming`, `component-set`, `variables`, `library`) come only from Figma tool results in this run. When the Figma source is `unreadable`, or a tool is missing or fails, record none of them for that source; do not infer them from screenshots, file names or `description.md`.
- Images and PDFs only produce `repetition` signals and candidates.
- A screenshot showing a component twice is not evidence of a component set or a library.

Mention the candidate count and the signal kinds found in the summary (one line).
