# Recommendations, strings placement and dependency changes

Use this file in plan steps 4–6. Scan's `findings[]` say where the project falls short of the platform's best practices; plan turns each one into a recommendation the user chooses at the approval gate. Build applies only the options the user picked.

## 1. Writing a recommendation

```json
{
  "id": "rec-colors-1",
  "finding_id": "colors-1",
  "title": "Move AppCard's hard-coded color into the theme",
  "why": "lib/core/widgets/app_card.dart:13 hard-codes Color(0xFFEEEEEE). Colors outside the theme don't follow dark mode or a rebrand, and drift from the design.",
  "options": [
    {"id": "keep", "label": "Keep as is", "changes": ["No change to existing code. New code still reads colors from the theme."], "files": []},
    {"id": "centralize", "label": "Move the color into AppColors", "changes": ["Add a cardBackground color to the AppColors theme extension with the current value", "Read it in AppCard via Theme.of(context).extension<AppColors>()"], "files": ["lib/core/theme/app_colors.dart", "lib/core/theme/app_theme.dart", "lib/core/widgets/app_card.dart"]}
  ],
  "choice": "keep"
}
```

- One recommendation per finding. `id` is `rec-<finding id>`.
- `why` cites the finding's paths (and line from its `detail`) and says in one or two plain sentences why it matters for this UI.
- `options`: `keep` first, always. Then one or two concrete options from section 2, adapted to the project: real file paths from the finding and the profile, real names from the code. `changes` are short imperative steps a reviewer can check; `files` lists every file the option touches.
- An option never touches code outside the finding's paths and what the new UI needs, unless its label says so explicitly ("…in every widget under lib/core/widgets").
- An option that adds a package says so in `changes` ("Add flutter_localizations (SDK) and intl to pubspec.yaml") and names the entry it would add to `dependency_changes` if chosen.
- `choice` is `"keep"`. Eval mode never changes it.
- Skip a finding whose area the new UI never touches (an `assets` finding when the design has no assets) and list it in `plan.md` as "not affected by this design".

## 2. Option templates by area

Platform names below are Flutter; for other platforms use the equivalent from that platform's build reference and the existing project configuration.

| Area | `keep` means | Change option(s) | Typical files |
|---|---|---|---|
| `theme` (no central theme, theme spread over widgets) | New tokens go where the project keeps styling today | `central-theme`: create one `ThemeData` with a `ColorScheme` and a `ThemeExtension` for custom tokens, wire it in the app root, move the values the new UI uses there | the theme file to create, the app root (`MaterialApp`), the finding's paths |
| `colors` (hard-coded color literals) | Existing literals stay; new code uses theme tokens | `centralize`: add each literal as a named token (a `ColorScheme` role when one fits by meaning, else a field on the project's `ThemeExtension`) and read it in the listed files | `theme.tokens_source`, `theme.location`, the finding's paths |
| `strings` (literals in widgets while localization exists) | Existing literals stay; new strings go into the project's system | `move-to-resources`: add a key per literal to the source-locale file (and every other locale with the source value marked for translation), replace the literals | the string files in `localization.location`, the finding's paths |
| `strings` (no localization at all) | New strings go into one feature strings class (section 4) | `localize`: set up the platform's localization system (section 4) and move the new strings there; optionally a second option that also moves the existing literals | `pubspec.yaml`, `l10n.yaml`, the new ARB file, the app root, the feature strings class |
| `rtl` (left/right instead of start/end, no `Directionality` handling) | Existing code stays; new code is directional | `directional`: replace `EdgeInsets.only(left:/right:)`, `Alignment.centerLeft`, `TextAlign.left` and similar in the listed files with their directional versions | the finding's paths |
| `previews` (shared components without previews) | New components still get a preview | `add-previews`: add a preview for each listed component using the project's existing preview pattern (a Widgetbook use case or an example/golden test). Flutter's `@Preview` widget previews are recent and experimental; offer them only when the project's Flutter version and code already use them | the listed components, the preview or test folder |
| `screenshot-tests` (no golden or snapshot tests) | Sauces' own verification goldens for the new UI are still written under `test/sauces/` | `add-goldens`: add golden tests for the listed shared components with the project's fonts loaded | `test/` paths for each listed component |
| `assets` (unorganized or duplicated assets, missing resolution variants) | New assets follow the existing layout | `organize`: the concrete fix the finding describes (declare the folder in `pubspec.yaml`, add `2.0x`/`3.0x` variants, remove a duplicate only if unused) | `pubspec.yaml`, the asset folder |
| `accessibility` (missing labels, small touch targets, fixed text sizes) | New code still meets the platform rules | `fix-a11y`: the concrete fix per listed file (semantic label, ≥ 48 dp target, respect text scaling) | the finding's paths |

## 3. Theme changes the design asks for

Scan findings are not the only source of recommendations. When the design differs from an existing theme value (`matching.md` section 4: a seed-derived color role, an existing text style, a component theme's radius), write one recommendation per theme file:

- `id`: `rec-design-theme-<n>`, `finding_id`: `design-theme-<n>` (there is no scan finding; the evidence is the design).
- `why`: each difference with the design value, the current value (or "derived from seed `#3D5AFE`") and the ΔE76 when known, and that `keep` means the new UI uses the existing roles and styles and verify reports the difference.
- Options (a theme change affects every screen, so each non-`keep` option's `label` ends with "(app-wide)", for example `Pin primary to #3D5AFE in AppTheme (app-wide)`):
  - `keep` (default): no change to the theme. New components use the nearest existing role or style; the differences are recorded on the items as expected fidelity notes.
  - `pin-roles`: set the listed roles or styles to the design values in the theme file (for Flutter, the named overrides of `ColorScheme.fromSeed(...)` and the `TextTheme` entries). `changes` must list every role or style it changes and the files that use them (grep the project for `colorScheme.<role>`, `textTheme.<style>` and the component theme), and warn that pinning a role breaks the Material 3 tonal derivation of its `on*` and `*Container` partners.
  - `fidelity-variant` (seed-based color schemes only): generate the scheme with `ColorScheme.fromSeed(seedColor: ..., dynamicSchemeVariant: DynamicSchemeVariant.fidelity)`, which keeps roles closer to the seed. Mark it "Flutter ≥ 3.22; verify in the project's Flutter version", and say that it shifts every role app-wide.
- `choice: "keep"`. Eval mode keeps it, so eval runs never change the existing theme.

Additive tokens (a new theme-extension field or text style only new components use) are plan items, not recommendations.

## 4. Where strings go

The plan lists strings; build writes them where this table says:

| `localization.system` | New strings go to |
|---|---|
| `arb` | The existing ARB files: the source locale gets the value, every other locale gets the source value marked for translation. Code reads them the way the project does (for example `context.l10n.loginTitle`). |
| `string-catalog` | The existing String Catalog (`.xcstrings`). |
| `strings-ios` | The owning target’s existing `.lproj` tables and `.stringsdict` files. |
| `strings-xml` | The existing `res/values/strings.xml`, plus `values-<locale>/strings.xml` for other locales. |
| `js-i18n` | The existing JS/TS message modules or locale catalogs. Preserve the existing translation API and key style. |
| `compose-resources` | The existing `composeResources/values/strings.xml`. |
| `none` | No new dependencies. Flutter: one feature-level strings class (for example `LoginStrings` in `lib/features/login/login_strings.dart`) holding every string of that feature; text kept there counts as not hard-coded. iOS: a new String Catalog (built in). Android: `strings.xml` (built in). KMP: use Compose resources if configured; otherwise keep source copy in a feature-level strings object until the resource integration is approved. React Native: a feature messages module until a localization integration is approved. |

When `localization.system` is `none`, always add a recommendation that offers proper localization, attached to scan's `strings` finding about missing localization (use `finding_id: "strings-localization"` if scan recorded none). For Flutter its `localize` option lists:

- `pubspec.yaml`: add `flutter_localizations: {sdk: flutter}` under `dependencies`, add `intl` (a version compatible with the Flutter SDK; `flutter_localizations` pins it, so `any` is acceptable), and set `flutter: generate: true`;
- `l10n.yaml` with `arb-dir`, `template-arb-file` and an explicit `output-dir` (recent Flutter versions deprecated the synthetic `flutter_gen` package; check the project's Flutter version);
- `lib/l10n/app_<source locale>.arb` with the planned keys;
- the app root: `localizationsDelegates` and `supportedLocales`;
- the matching `dependency_changes` entries, added only when the user picks this option.

RTL: when `localization.rtl` is true, every new string and layout must work right-to-left; note in the screen item that build uses directional padding and alignment.

## 5. Dependency changes

`dependency_changes[]` entries are `{package, version, scope: "dev"|"main", reason}`. List only what build will add for the plan as it stands; entries for options the user has not picked are not listed. Before listing a package, check the project's manifest (`pubspec.yaml`, `Package.swift`, Gradle version catalog) to see whether it is already there.

Screenshot tooling, needed by verify:

| Platform | When the project has none (`screenshot_tooling.present: false`) |
|---|---|
| Flutter | Nothing: golden tests use `flutter_test`, which ships with the SDK. Fonts come from the project's own assets. |
| iOS SwiftUI | Use existing XCTest UI tests when available. If a dedicated snapshot dependency is approved, add `swift-snapshot-testing` (pointfreeco) to the test target. |
| Android Compose | Use existing Compose instrumentation when available. If a host-side screenshot dependency is approved, add Roborazzi with Robolectric to the appropriate test configuration. |
| Compose Multiplatform | Reuse the configured Android or iOS test host. Do not create a desktop target solely for verification. |
| React Native | Use the existing device test harness or scripted capture. Propose a new runner only when the project needs one and list its dependencies for approval. |

When the project already has screenshot tooling, use it and add nothing. Adding tooling always goes through this list and the approval gate; never add it silently.

SVG icons (Flutter): plan the nearest `Icons.*` match with a note on the difference (`matching.md` section 3). List `flutter_svg` (`scope: "main"`) only when all three hold: the design has SVG icons, `pubspec.yaml` lacks `flutter_svg`, and an exact icon match matters (brand marks, illustrations, icons with no close built-in). State the reason.

Versions: write the constraint the project's manifest format expects (for pub, a caret constraint such as `^2.0.0`). If you are not sure which version is current, use the newest one you know, and say in `plan.md` that build should confirm it before adding it.
