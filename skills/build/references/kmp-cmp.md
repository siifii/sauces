# Build Compose Multiplatform

## Tokens
Reuse the common MaterialTheme and shared token types. Keep device-specific theme overrides in their existing platform source sets.

## Components
Build stateless shared @Composable functions with immutable inputs, Modifier and event lambdas. Use common Compose semantics and logical alignment. Treat any native-only component as a platform boundary.

## Previews and tests
Use the preview annotation available to the project's Compose plugin and source set or its existing preview harness. Seed each UI state. Use the configured Compose UI test runner for semantics, actions and RTL, including actual mobile hosts when available.

## Strings
Use the project's generated Res.string and Res.plurals via Compose Multiplatform resource accessors. Add and update commonMain/composeResources/values[-locale] entries. Keep defaults complete and record missing translations in todos.json. Resolve the actual generated Res package from the build.

## Assets
Use commonMain/composeResources/drawable with the generated Res accessors. Verify the asset format works on both mobile hosts. Keep host-only assets in their existing native locations.

## State
Keep seeded UI state shareable in commonMain. Follow existing StateFlow/ViewModel and DI wiring. Route native concerns through existing interfaces or expect/actual declarations.

## Folders
Write common UI to the module's commonMain Kotlin and composeResources roots. Put host integration in the corresponding platform source set or launcher.

## Checks
Discover Gradle tasks and compile common code and the configured mobile targets. Assemble an Android host when present. Build and launch the iOS host through its Xcode scheme on macOS when present. Keep the iOS host’s CADisableMinimumFrameDurationOnPhone Info.plist value set to true so the Compose controller passes startup validation. [JetBrains UIKit integration guide](https://kotlinlang.org/docs/multiplatform/compose-uikit-integration.html) Run configured common/host tests and record results by target. Add approved dependencies to their actual source set. Run lint_generated.py with --platform kmp-cmp.

## Don't
Keep Android R, android.* and Apple APIs outside commonMain. Avoid introducing a desktop target just to render a mobile design.
