# Scan Android Compose

- Read settings.gradle(.kts), included module build files and version catalogs. Resolve plugin aliases and confirm a Compose app module with a launcher manifest and Compose source. Record library modules that host UI, but keep the Gradle wrapper root as the project root.
- Follow the launcher activity, NavHost and MaterialTheme call. Record the actual theme function file and the files defining ColorScheme, Typography or custom CompositionLocals. Read build types and flavors to find the source sets used by the app.
- Infer `mvvm` from ViewModels exposing UI state to the view and `mvi` from an explicit intent/event and reducer loop. Record `viewmodel` or the observed state library. Record `hilt` or `koin` only when wiring exists.
- Inventory public reusable @Composable functions and their named parameters. Exclude navigation destinations, screen hosts and preview functions. Resolve previews by the functions they call, including multi-previews.
- Record `strings-xml` for res/values/strings.xml and qualifiers such as values-ar or values-b+zh+Hans. Use the res directory as location. Check supported RTL and actual directional modifier use.
- Record evidenced screenshot tooling such as Roborazzi, Paparazzi, Compose Preview Screenshot Testing or instrumentation capture. A test dependency alone for semantics assertions is insufficient.
- Derive component structure from existing paths: components split by atoms/molecules/organisms, tokens and components layers, or features with shared UI. Use the common scan finding rules with the Kotlin lint rules and allow the actual token sources.
