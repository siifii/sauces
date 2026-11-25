# Scan Compose Multiplatform

- Read settings.gradle(.kts), version catalogs and module builds to locate the module applying Kotlin Multiplatform and Compose. Confirm shared composables under commonMain and enumerate actual mobile target declarations, such as androidTarget or androidLibrary and iosArm64/iosSimulatorArm64. Treat Android and iOS launchers consuming that module as hosts.
- Follow the shared App composable and record its theme, token files and custom CompositionLocals. Document platform overrides in androidMain/iosMain and expect/actual pairs when present.
- Inventory reusable public commonMain composables with their parameters and linked previews. Record platform-only components with their actual paths and explain source-set restrictions in conventions. Derive component structure from shared source folders.
- Recognize `compose-resources` from commonMain/composeResources/values and generated Res imports. Enumerate locale qualifiers, record the composeResources folder, and check logical-direction layout and RTL locale support.
- Distinguish ViewModel/StateFlow MVVM from intent/reducer MVI. Record the state and DI libraries actually wired in commonMain (for example Koin). Inspect platform launchers for injection boundaries.
- Record screenshot tooling only when an actual capture runner is configured. Shared semantics tests alone do not establish screenshot tooling. Use common scan finding rules with the Kotlin lint rules and allow the actual token sources.
