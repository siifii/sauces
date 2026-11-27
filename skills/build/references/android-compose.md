# Build Android Compose

## Tokens
Read existing MaterialTheme.colorScheme, typography, shapes and any custom CompositionLocals. Add design-specific values to the planned token files. Use dp for layout and sp for text. Respect planned decisions about dynamic color.

## Components
Use stateless @Composable functions receiving immutable inputs and event lambdas. Accept a Modifier and apply it to the outermost layout. Use Material semantics, meaningful labels for actionable icons, null descriptions for decorative icons, and logical start/end padding. Preserve parameters and defaults when extending a component.

## Previews and tests
Wrap @Preview examples in the actual app theme and seed data for each state. Follow existing Compose UI tests and assert semantics and actions, including RTL when enabled.

## Strings
Use stringResource and pluralStringResource with module-local R.string/R.plurals. Add source entries under res/values and update the corresponding locale overrides according to project policy. Let missing translations fall back to source where appropriate and record them in todos.json. Preserve substitutions and XML escaping. If a plain LTR placeholder must be copied into RTL resources, enclose its text in LRI and PDI (XML `&#x2066;` and `&#x2069;`) to keep punctuation in order. Apply the same rule to displayed plural branches.

## Assets
Reuse approved vectors or painterResource IDs. Use VectorDrawable XML for compatible SVG shapes and appropriately qualified raster resources otherwise. Use autoMirrored only for directional artwork.

## State
Expose a state-in/events-out screen composable. Wire its route to the existing ViewModel and collect lifecycle-aware StateFlow if available. Keep unknown business actions as TODO(sauces).

## Folders
Put Kotlin and resources in the owning Gradle module/source set and follow its feature, navigation and shared UI conventions.

## Checks
Discover the actual module and variant tasks. For a standard app module run ./gradlew :app:assembleDebug :app:lintDebug :app:testDebugUnitTest. Run applicable connected tests when a device is available and report unavailable checks. Use the plan’s approved dependency versions or its approved BOM. Inspect the resolved Android test runtime with Gradle dependencyInsight before running on the device, including the transitive Espresso version. If instrumentation fails in AndroidX with a reflective InputManager.getInstance error, verify platform compatibility and propose an aligned test dependency update before retrying. Check the resolved version again after changing Compose UI test dependencies. Espresso 3.7.0 replaced that reflection call. [AndroidX Test release notes](https://developer.android.com/jetpack/androidx/releases/test) Put approved dependencies in the module and existing version catalog. Run lint_generated.py with --platform android-compose.

## Don't
Avoid introducing new architecture or changing app-wide theme roles without approval. Avoid Android-specific declarations in shared multiplatform source sets.
