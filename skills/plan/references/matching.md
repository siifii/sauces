# Matching design elements to the project

Use this file in plan step 3 to turn the manifest's layouts into `items[]`. Inputs: every state `layout` (nodes `{type, children?, text?, style?, component?, confidence}`, see `${CLAUDE_PLUGIN_ROOT}/agents/design-analyst.md`), `manifest.tokens`, `manifest.assets`, and the profile's `components[]`, `theme` and `conventions`. Read each existing component's source before matching: its parameters, their types and defaults, and what it renders.

## 1. Collect elements

1. Walk every state's layout depth first and collect the `component` nodes. Skip device chrome (`system-bar`) and pure decoration (`divider` with no variant).
2. Merge the same element across states into one element: same screen, same kind, same position in the tree and same text or role (the email field in default, error and loading is one element). Its variants across states (`error`, `loading`, `disabled`) are requirements on the component, not separate elements.
3. Two elements of the same kind on one screen (email and password fields) are separate elements that may map to the same component. Plan one item per element, so each `design_ref` is traceable.
4. A part drawn inside a component belongs to that component: an eye icon inside a text field is the field's trailing icon, a spinner inside a button is the button's loading state, error text right under a field is the field's error text. Never plan those parts as separate buttons or fields.
5. Plain text nodes (titles, body copy) and layout containers are not components. They belong to the screen item, styled by theme type tokens (section 4). Plan a component for a group only when it is a real reusable unit (a form used on two screens, a card that repeats).
6. One `screen` item per screen, covering its states. Its `notes` list the states, the elements it composes and the `TODO(sauces)` behavior (submit, navigation, validation) build must not guess.

`design_ref` is `<screen>/<state>#<element>`, using the first state where the element appears and a short element name from its kind and role: `login/default#button`, `login/default#email-field`, `login/default#password-field`, `login/error#error-text`, `login/default#forgot-link`. A screen item uses `<screen>/<state>#screen`; a token item uses `tokens#<role>` (`tokens#primary`, `tokens#title`).

## 2. Match against existing components

For each element, compare with every entry in `components[]`:

- **Kind fit.** The component renders the same kind of control. Judge from the source, not only the name: `AppButton` wrapping `FilledButton` is a filled button; `AppTextField` wrapping `TextField` with `InputDecoration` is a text field.
- **Param fit.** Each piece of content or variant the element shows needs a parameter: label text ↔ `label`, error text or error variant ↔ `errorText`, masked value ↔ `obscure`, tap ↔ `onPressed`, loading spinner ↔ `loading`, trailing icon ↔ `suffixIcon`/`trailing`. Example: a design text field with a label and an error state ↔ `AppTextField(label, errorText)` is a full fit.
- **Look fit.** The component's built-in styling (height, radius, fill, border) is close to the design or comes from the theme, so a token change fixes the difference.

Score `confidence` from 0 to 1:

| Confidence | When | Decision |
|---|---|---|
| ≥ 0.8 | same kind, every content piece and variant already has a parameter, look fits or comes from the theme | `reuse` |
| 0.5–0.8 | same kind, but one or two additive parameters or variants are missing (a `loading` flag, a trailing icon) | `extend` |
| < 0.5 | no component of that kind, or the fit would need a breaking change | `new` |

For `reuse`, `path` and `existing_path` are the component's file. Note which parameters the screen will pass.

For `extend`, `path` and `existing_path` are the component's file, and `notes` must state:

- the exact additive change: parameter name, type and default (`add bool loading = false: shows a 24 px spinner instead of the label and disables taps`; `add Widget? suffixIcon = null: trailing icon inside the field`);
- that existing call sites keep working because every new parameter is optional with a default that keeps today's behavior.

Never plan an `extend` that removes or renames a parameter, changes a default, or changes what existing callers see. If the fit needs that, plan a `new` component (or a wrapper around the existing one) and say why.

Never plan to replace, rename, move or delete a user component, and never plan a `new` component that duplicates one that exists (a second button when `AppButton` fits with an extension).

For `new`:

- Name it the way the project names that kind (`conventions.naming`: for example an `App` prefix for shared widgets, `<Feature>` prefix for feature widgets), after its design kind and role (`AppLink`, `LoginHeader`), not after the platform widget that implements it.
- Before planning a wrapper for a built-in control, check how the project's pages already render that kind. If pages use the platform's built-in widget directly (a `TextButton` for links), do the same: the element becomes part of the screen item (say so in its `notes`) instead of a new component, unless it repeats on ≥ 2 screens or needs styling the theme cannot give.
- Choose `level` by composition: `atom` (one control), `molecule` (a few atoms with one job: a labelled field with its error), `organism` (a section: a login form, an app bar), `screen`.
- `path` is the file in the chosen structure's folder for that level (`design-system-patterns.md` section 3) named with the project's file convention (`lib/core/widgets/app_link.dart`).

## 3. Assets

For each `manifest.assets` entry and each `icon` node:

- Reuse an asset already in the project when it is the same image (compare names and look).
- An icon close to one in the platform's icon set the project already uses (Material `Icons.*`, SF Symbols): plan the nearest built-in icon and note the difference ("Icons.visibility_outlined: stroke slightly heavier than the 1.75 px design icon"). This needs no new dependency.
- When an exact match matters (brand marks, illustrations, or an icon set the built-ins do not cover), plan a `new` asset item (`level: "atom"`, `path` in the project's asset folder) and, if the platform needs a package to render it and the project lacks it, a `dependency_changes` entry (`recommendations.md` dependency section).

## 4. Tokens

Map every design token to the project's theme before planning anything new:

- **Colors.** Compare each design color with the colors the theme defines: literal values in the theme files and in `theme.tokens_source` (theme extensions, color files, asset catalogs). Two colors are the same when CIE76 ΔE < 3. A match means the item uses that existing token; no `token` item.
- **Derived colors.** A seed or generated palette (for example a seed-based color scheme) has no literal value per role, and its generated roles usually differ from the seed. Do not assume a role matches. Map the design color to the role by meaning (`primary` for the main button fill, `onSurface` for body text, `outline` for field borders, `error`), and when the design needs the exact value, plan one `token` item per theme file that pins those roles, listing each role → hex in `notes`, and say that it changes those roles app-wide.
- **Typography.** Map each design style to the theme's type scale by size and role (`28/36 600` → the headline style closest to 28). When weight, size, line height or letter spacing differ, plan a `token` item that adjusts that style in the theme (one item per theme file, each change in `notes`). Never plan per-widget font overrides when the theme can carry the style.
- **Spacing and radii.** If the project has spacing or radius tokens, map to them. If it writes these values inline, follow that; do not invent a token system (a recommendation may offer one).
- **Genuinely new values** (a color with no role match and ΔE ≥ 3 to everything) become `token` items with `decision: "token"`, `level: "token"`, `confidence: 1`, `path` = the file where the project keeps that kind of token, and the name and value in `name`/`notes`.

A `token` item never deletes or renames an existing token. Changing an existing token's value is allowed only as a `token` item whose `notes` say what else uses it.
