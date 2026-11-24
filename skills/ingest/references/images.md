# Analyzing state images

Every state reference gets a `layout`: a tree describing what the image shows. `plan` maps its components to project components, `build` implements it, and `verify` checks the result against the same image.

## Device pixel ratio

Measure in logical px. Pick the DPR from the image width:

| Image width | Assume DPR | Logical width |
|---|---|---|
| 1170–1320 | 3 | 390–440 |
| 720–900 (e.g. 780) | 2 | 360–450 |
| 320–450 | 1 | same |

Anything else: choose the DPR that gives a logical width between 320 and 450 (tablets: up to 1024). A PDF raster's DPR follows from its width the same way. Record the assumption on the layout root (`"assumed_dpr": 2`) and mention it in the summary.

## Dispatching design-analyst

When the Agent (Task) tool is available, dispatch `sauces:design-analyst` once per unique state reference, all in one message so they run in parallel. Prompt each with:

```
Image: <absolute path to .sauces/references/<screen>--<state>.png>
Size: <width>x<height> px. Assume DPR <n> (logical <w>x<h>) unless the image proves otherwise.
Screen: <screen id>. State: <state id> (<state name>).
Known copy (supplementary, from <file>, only if present): <exact strings>
Return only the JSON object from your output contract.
```

Get the absolute path with `pwd`. Pass known copy only from a `description.md`/`README.md` beside the designs, and only as a hint for spelling: the agent reports what the image shows.

Each agent returns one JSON object `{screen, state, layout}`. Parse it. If it is not valid JSON or misses `layout`, re-dispatch once with the parse error; if it fails again, analyze that image yourself. Store `layout` (the root node, with `assumed_dpr`) on the state. Ignore its `screen`/`state` fields except as a cross-check: if the agent disagrees with your grouping (for example it sees a spinner in a state named `default`), look again and fix the grouping or note the disagreement in the source's `reason`.

Without the Agent tool, read each image and produce the same JSON yourself, following the contract in `${CLAUDE_PLUGIN_ROOT}/agents/design-analyst.md`.

## The layout contract (summary)

Node: `{type, children?, text?, style?, component?, confidence}`.

- `type`: `column`, `row`, `stack` (overlapping children), `text`, `image`, `component`.
- `text`: the exact visible string (for `text` nodes and labelled components).
- `style`: any of `color`, `background`, `size`, `weight`, `line_height`, `family`, `radius`, `padding` (number or `[top, right, bottom, left]`), `gap`, `border` (`{width, color}`), `width`, `height`, `align`. Raw logical px, not snapped. Colors as `#RRGGBB`.
- `component`: `{kind, variant}` with kind such as `button`, `text-field`, `link`, `icon`, `icon-button`, `checkbox`, `switch`, `card`, `list-item`, `app-bar`, `tab-bar`, `progress`, `divider`, `image`, `avatar`, `chip`; variant such as `filled`, `outlined`, `text`, `error`, `loading`, `disabled`.
- `confidence`: 0–1 for the node's type/component identification.
- Optional: `placeholder: true` on sample content (example emails, masked passwords), `description` for unlabelled icons. The full contract is in `${CLAUDE_PLUGIN_ROOT}/agents/design-analyst.md`.

## Snapping spacing and radii to the 4-pt grid

Layouts keep raw values. Tokens get snapped values:

1. Collect every `padding` side, `gap` and `radius` from all layouts (raw logical px). Ignore border widths and sizes.
2. Snap: values of 0 stay 0 (and are not recorded); values below 3 snap to 2 (hairline spacing); everything else rounds to the nearest multiple of 4 (14 → 16, 10 → 12, 6 → 8; a tie rounds up).
3. A fully rounded shape (pill or circle, radius ≥ half its height) records `radius` as half its height in the layout, and that value snapped in `radii`.
4. De-duplicate, sort ascending, and write `tokens.spacing` and `tokens.radii`.
5. When a raw value differs from its snapped value by more than 1 px, add it to the layout node's style as `"raw_note": "gap 14 → 16"`, so `plan` can decide whether the design meant it.
