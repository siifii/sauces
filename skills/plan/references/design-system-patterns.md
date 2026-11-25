# Design-system patterns

Use this file to choose how new components are organized, to fill `plan.json` `structure`, and to set every item's `layer`. Inputs: `.sauces/manifest.json` `design_system` and the state `layout`s (written by ingest; `design_system` may be missing) and `.sauces/project-profile.json` `mode` and `projects[].component_structure` (written by scan; it may be missing).

Modes map to the profile's `mode` like this: `existing` is follow/advise mode; `ambiguous` becomes follow/advise mode once the user (or eval mode) picked an existing project; `empty` is create mode.

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
- **When it fits.** Follow/advise mode (profile `mode: "existing"`, or `"ambiguous"` after an existing project was picked), whenever scan found a structure for that project (`component_structure.pattern` is `atomic`, `layered`, `feature-first` or `custom`). It is never offered in create mode (`mode: "empty"`) or when the structure is missing or `none`. When it is offered, it is always the recommendation (section 4).
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

Locate the owning source root from the profile and build descriptors. For Android use the app module’s Kotlin package root (it may be under `src/main/java`). For CMP use the shared module’s `commonMain/kotlin` package root. For SwiftUI use the actual app or SwiftPM target folder and ensure new files belong to the target.

| Pattern | Compose and Compose Multiplatform | SwiftUI |
|---|---|---|
| `atomic` | `designsystem/{tokens,atoms,molecules,organisms}/`, `features/<feature>/` | `DesignSystem/{Tokens,Atoms,Molecules,Organisms}/`, `Features/<Feature>/` |
| `layered` | `designsystem/{tokens,foundations,components,patterns}/`, `features/<feature>/` | `DesignSystem/{Tokens,Foundations,Components,Patterns}/`, `Features/<Feature>/` |
| `feature-first` | `core/{theme,ui}/`, `features/<feature>/{ui,state}/` | `Core/{Theme,UI}/`, `Features/<Feature>/{Views,State}/` |

Use these as defaults for new projects. Keep localized strings and images in their platform resource locations, and use the observed project paths and naming in follow mode.

### React Native

Use the existing application source root (for example `src/`). For atomic layouts use `design-system/{tokens,atoms,molecules,organisms}/`. For layered layouts use `design-system/{tokens,foundations,components,patterns}/`. For feature-first layouts use `shared/{theme,ui}/` and `features/<feature>/`. Keep Expo Router entry files in the actual route tree and the feature screen implementation outside it. In follow mode use the app's observed paths and naming.

## 3. Level → layer

| `level` | `atomic` | `layered` | `feature-first` | `follow` |
|---|---|---|---|---|
| `token` | `tokens` | `tokens` (values); `foundations` when the item is theme wiring, a type style or an icon set | `core-theme` | the theme folder (`theme.location`'s folder) |
| `atom` | `atoms` | `components` | `core-widgets` | the shared widget folder |
| `molecule` | `molecules` | `components` | `core-widgets` when used on ≥ 2 screens or by another shared component, else `feature-widgets` | the shared widget folder when used on ≥ 2 screens, else the feature's widget folder (or the page file's folder when the project has no feature widget folder) |
| `organism` | `organisms`; `templates` when it is a page layout with slots (`body`, `header`) and no content of its own | `components` when it is a reusable control (app bar, navigation bar, dialog, card); `patterns` when it is a feature-agnostic composition (form, empty state, list-detail) | `feature-widgets`; `core-widgets` when used by ≥ 2 features | as for `molecule` |
| `screen` | `screens` | `screens` | `feature-view` | the project's page folder for that feature (for example `lib/features/<f>/view`) |

An item that `reuse`s or `extend`s an existing component keeps that component's current folder as its `path`; set `layer` to the layer that folder plays (for `follow`, the folder itself). Never move an existing file to make it fit.

## 4. Scoring

### Follow wins when it is offered

When `follow` is offered (section 1), it is always `recommended`, whatever the scores below. Score the other three patterns only to order the alternatives in `options`, and when one of them has a strong signal (any row below that applies to it), say so in `reasons`.

### Scoring the other patterns

Start `atomic`, `layered` and `feature-first` at 0 and add points from this table. Each row applies at most once.

| Signal | Points |
|---|---|
| `design_system.signals` has a `figma-naming` signal with atomic terms (`Atoms`, `Molecules`, `Organisms`, `Templates`) | `atomic` +3 |
| a `component-set` signal with ≥ 3 variants | `layered` +2 |
| a `variables` signal that says the variables are tiered (primitive → semantic) | `layered` +2 |
| a `library` signal | `layered` +2 |
| ≥ 6 distinct reused kinds across ≥ 3 distinct screens | `layered` +2 |
| ≤ 3 distinct reused kinds, or every component on 1 screen | `feature-first` +2 |

Counting kinds for the last two rows:

- Count distinct `component.kind` values (`text-field`, `button`, …), not candidate names: two Figma components of the same kind count once.
- A kind is **reused** when it appears ≥ 2 times within one state, or on ≥ 2 screens. Read this from the state `layout`s in the manifest (walk each state's `component` nodes); `component_candidates[].screens` gives the screens. The same element repeated across the states of one screen (the button in default, error and loading) is not reuse, even though it raises `occurrences`.
- Screens are the union of the reused kinds' `screens`.

A missing `design_system` and no layouts score nothing from this table.

Without `follow`, the highest score is `recommended`. Break ties in this order, lightest first: `feature-first` > `layered` > `atomic`.

Example: the flutter-bloc fixture (structure `feature-first`) with the login design. `follow` is offered, so it is recommended. For ordering: one screen, and only `text-field` is reused (2 per state), so `feature-first` 2, `layered` 0, `atomic` 0. Options: `follow`, `feature-first`, `layered`, `atomic`.

Do not add points for anything outside this table. If the user states a preference ("we use Atomic Design"), that is their choice at the gate, not a score.

## 5. Writing `structure`

```json
"structure": {
  "recommended": "follow",
  "choice": "follow",
  "reasons": ["Your project already keeps shared widgets in lib/core/widgets and screens in lib/features/<feature>/view, so new code goes there too.", "The design is a single login screen where only the text field repeats (twice per state), too small to justify a separate design-system folder."],
  "options": [
    {"id": "follow", "label": "Follow the project's structure", "folders": ["lib/core/widgets", "lib/features"]},
    {"id": "feature-first", "label": "Feature-first with a shared core", "folders": ["lib/core/theme", "lib/core/widgets", "lib/features/<f>/widgets", "lib/features/<f>/view"]},
    {"id": "layered", "label": "Layered design system (Material 3 style)", "folders": ["lib/design_system/tokens", "lib/design_system/foundations", "lib/design_system/components", "lib/design_system/patterns", "lib/features/<f>/view"]},
    {"id": "atomic", "label": "Atomic Design", "folders": ["lib/design_system/tokens", "lib/design_system/atoms", "lib/design_system/molecules", "lib/design_system/organisms", "lib/design_system/templates", "lib/features/<f>/view"]}
  ]
}
```

- `options`: every offered pattern, the recommended one first, then the others by score (ties in the tie-break order). `folders` come from section 2 (for `follow`, the scanned paths).
- `choice`: starts equal to `recommended`. The user may pick another option at the approval gate. In eval mode (`.sauces/eval-approve` exists) keep the recommendation.
- `reasons`: 2–4 short plain sentences a developer who has never heard of the pattern names would understand. Each one cites a concrete signal with its numbers or folders (the scanned folders, the candidate counts, the Figma naming or variables). Name a strong signal for a pattern that lost when it matters ("The Figma file names pages Atoms and Molecules, but the project already has its own structure, so following it avoids two systems side by side."). No score numbers, no jargon without a gloss.
- Switching away from `follow` in an existing project applies to new code only. Moving existing files into the new structure is a separate recommendation whose `choice` defaults to `keep`.

After the choice, set every item's `layer` from section 3 and make its `path` sit in that layer's folder.
