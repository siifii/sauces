# Design-system patterns

Use this file to choose how new components are organized, to fill `plan.json` `structure`, and to set every item's `layer`. Inputs: `.sauces/manifest.json` `design_system` (written by ingest; it may be missing) and `.sauces/project-profile.json` `mode` and `projects[].component_structure` (written by scan; it may be missing).

Each plan item keeps its universal `level` (`token`, `atom`, `molecule`, `organism`, `screen`). The chosen pattern turns that level into a `layer` and the layer into a folder.

## 1. The four patterns

### `atomic`: Atomic Design

- **What it is.** Components are built up from the smallest pieces: atoms (a button, a text field, an icon) → molecules (a labelled field with its error text) → organisms (a login form) → templates (page layouts with slots, no real content) → screens (templates filled with real content and state).
- **When it fits.** The design is already named that way (Figma pages or components like `Atoms/Button`), or the team says it thinks in atomic terms.
- **Layers.** `tokens`, `atoms`, `molecules`, `organisms`, `templates`, `screens`.

### `layered`: Layered design system (Material 3 / Carbon / Polaris style)

- **What it is.** A design system split by responsibility: tokens (raw values) → foundations (theme wiring, type styles, icons, elevation) → components (the reusable controls, each with variants) → patterns (recurring compositions such as forms or empty states) → screens.
- **When it fits.** A Figma library with component sets and variants, tiered variables (primitive → semantic), a published library, or a multi-screen app with many reused components.
- **Layers.** `tokens`, `foundations`, `components`, `patterns`, `screens`.

### `feature-first`: Feature-first with a shared core

- **What it is.** A small shared core (theme plus the few widgets used everywhere) and everything else inside the feature that uses it.
- **When it fits.** Small designs, one or two screens, few reused components.
- **Layers.** `core-theme`, `core-widgets`, `feature-widgets`, `feature-view`.

### `follow`: Follow the project's existing structure

- **What it is.** Put new code where the project already puts that kind of code, using the folders scan found.
- **When it fits.** Follow and advise mode, whenever scan found a structure (`component_structure.pattern` is not `none`). It is never offered in create mode (profile `mode: "empty"`) or when the structure is missing or `none`.
- **Layers.** The layer is the existing folder the item goes into, written as its path relative to the target root (for example `lib/core/widgets`). Pick it from `component_structure.paths`, the `components[].path` folders and `conventions.feature_folders`.

## 2. Folder mapping per platform

### Flutter

| Pattern | Folders |
|---|---|
| `atomic` | `lib/design_system/tokens/`, `lib/design_system/atoms/`, `lib/design_system/molecules/`, `lib/design_system/organisms/`, `lib/design_system/templates/`; screens in `lib/features/<f>/view/` |
| `layered` | `lib/design_system/tokens/`, `lib/design_system/foundations/`, `lib/design_system/components/`, `lib/design_system/patterns/`; screens in `lib/features/<f>/view/` |
| `feature-first` | `lib/core/theme/`, `lib/core/widgets/`; per feature `lib/features/<f>/widgets/` and `lib/features/<f>/view/` |
| `follow` | the folders in `profile.projects[].component_structure.paths`, used as they are |

Use the project's own prefix when it has one (for example `lib/src/` instead of `lib/`). Put state management next to the screen the way the project does it (`lib/features/<f>/cubit/` beside `view/` for flutter_bloc), whatever the pattern.

### Compose, Compose Multiplatform, SwiftUI

| Platform | Folders |
|---|---|
| Android Compose | Defined in the next plans. |
| Compose Multiplatform (`commonMain`) | Defined in the next plans. |
| SwiftUI | Defined in the next plans. |

Until then, offer only `follow` (when scan found a structure) and `feature-first` adapted to the platform's usual folders, and say in the plan that the full mapping comes in a later Sauces version.

## 3. Level → layer

| `level` | `atomic` | `layered` | `feature-first` | `follow` |
|---|---|---|---|---|
| `token` | `tokens` | `tokens` (values); `foundations` when the item is theme wiring, a type style or an icon set | `core-theme` | the theme folder (`theme.location`'s folder) |
| `atom` | `atoms` | `components` | `core-widgets` | the shared widget folder |
| `molecule` | `molecules` | `components` | `core-widgets` when used on ≥ 2 screens or by another shared component, else `feature-widgets` | the shared widget folder when used on ≥ 2 screens, else the feature's widget folder (or the page file's folder when the project has no feature widget folder) |
| `organism` | `organisms`; `templates` when it is a page layout with slots (`body`, `header`) and no content of its own | `patterns` | `feature-widgets`; `core-widgets` when used by ≥ 2 features | as for `molecule` |
| `screen` | `screens` | `screens` | `feature-view` | the project's page folder for that feature (for example `lib/features/<f>/view`) |

An item that `reuse`s or `extend`s an existing component keeps that component's current folder as its `path`; set `layer` to the layer that folder plays (for `follow`, the folder itself). Never move an existing file to make it fit.

## 4. Scoring

Start every offered pattern at 0. Add points from this table. Each row applies at most once.

| Signal | Points |
|---|---|
| `design_system.signals` has a `figma-naming` signal with atomic terms (`Atoms`, `Molecules`, `Organisms`, `Templates`) | `atomic` +3 |
| a `figma-naming` signal with at least two layered terms (`Foundations`, `Tokens`, `Components`, `Patterns`) | `layered` +2 |
| a `component-set` signal with ≥ 3 variants | `layered` +2 |
| a `variables` signal that says the variables are tiered (primitive → semantic) | `layered` +2 |
| a `library` signal | `layered` +2 |
| `component_candidates`: ≥ 6 distinct reused kinds (candidates with `occurrences` ≥ 2) across ≥ 3 distinct screens (union of their `screens`) | `layered` +2 |
| `component_candidates`: ≤ 3 distinct reused kinds, or all candidates on 1 screen | `feature-first` +2 |
| follow or advise mode and `component_structure.pattern` is `atomic`, `layered`, `feature-first` or `custom` | `follow` +4 |

Offered patterns: `atomic`, `layered`, `feature-first` always; `follow` only when the last row's condition holds. A missing `design_system` simply scores nothing from the first seven rows.

The highest score is `recommended`. Break ties in this order, lightest first: `follow` > `feature-first` > `layered` > `atomic`. Example: the flutter-bloc fixture with the login design scores `follow` 4 (structure `feature-first`), `feature-first` 2 (one screen), `layered` 0, `atomic` 0, so `follow` is recommended.

Do not add points for anything outside this table. If the user states a preference ("we use Atomic Design"), that is their choice at the gate, not a score.

## 5. Writing `structure`

```json
"structure": {
  "recommended": "follow",
  "choice": "follow",
  "reasons": ["Your project already keeps shared widgets in lib/core/widgets and screens in lib/features/<feature>/view, so new code goes there too.", "The design is one screen with 3 reused component kinds, too small to justify a separate design-system folder."],
  "options": [
    {"id": "follow", "label": "Follow the project's structure", "folders": ["lib/core/widgets", "lib/features"]},
    {"id": "feature-first", "label": "Feature-first with a shared core", "folders": ["lib/core/theme", "lib/core/widgets", "lib/features/<f>/widgets", "lib/features/<f>/view"]},
    {"id": "layered", "label": "Layered design system (Material 3 style)", "folders": ["lib/design_system/tokens", "lib/design_system/foundations", "lib/design_system/components", "lib/design_system/patterns", "lib/features/<f>/view"]},
    {"id": "atomic", "label": "Atomic Design", "folders": ["lib/design_system/tokens", "lib/design_system/atoms", "lib/design_system/molecules", "lib/design_system/organisms", "lib/design_system/templates", "lib/features/<f>/view"]}
  ]
}
```

- `options`: every offered pattern, the recommended one first, then by score (ties in the tie-break order). `folders` come from section 2 (for `follow`, the scanned paths).
- `choice`: starts equal to `recommended`. The user may pick another option at the approval gate. In eval mode (`.sauces/eval-approve` exists) keep the recommendation.
- `reasons`: 2–4 short plain sentences a developer who has never heard of the pattern names would understand. Each one cites a concrete signal with its numbers or folders (the scanned folders, the candidate counts, the Figma naming or variables). Name a strong signal for a pattern that lost when it matters ("The Figma file names pages Atoms and Molecules, but the project already has its own structure, so following it avoids two systems side by side."). No score numbers, no jargon without a gloss.
- Switching away from `follow` in an existing project applies to new code only. Moving existing files into the new structure is a separate recommendation whose `choice` defaults to `keep`.

After the choice, set every item's `layer` from section 3 and make its `path` sit in that layer's folder.
