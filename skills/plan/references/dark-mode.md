# Dark mode

Dark mode is an **appearance** of a screen state, not a different state. A dark frame of the default state is the state `default-dark` with `"appearance": "dark"`; its light twin is `default` (appearance light, or no field). Every stage treats the pair as one state seen two ways.

## Ingest

- A frame is dark when its name says so (`-dark`, `_dark`, `dark/` folder, a Figma page or frame named Dark) or, failing that, when its background is dark (mean luminance under about 20%) and its layout matches a light frame of the same screen (same text, same structure).
- Pair it with the light frame of the same screen and state: id `<state>-dark`, `name` the light state's name (`default`, `error`…), `appearance: "dark"`, reference `.sauces/references/<screen>--<state>-dark.png`. Light and dark frames are **never duplicates** of each other.
- A dark frame with no light twin is still `<state>-dark`; say in its `reason` that the light version was not designed.
- Tokens: record dark colors as the dark value of the same token (`surface` light `#FFFFFF`, dark `#1B1B1F`), never as new unrelated tokens, and never invent a dark value the design does not show.

## Plan

- Project **has** a dark theme (Flutter `darkTheme`/`ThemeMode`, Compose `darkColorScheme`, SwiftUI asset colors with Dark appearances, CSS `prefers-color-scheme` or a `.dark`/`[data-theme=dark]` class, Tailwind `dark:`, React Native `useColorScheme` themes): map each dark token onto it. New dark values are additive token items like light ones.
- Project has **no** dark theme: do not build one silently. Add an advise **recommendation** ("Add a dark theme: the design has N dark frames"), default "keep as is". If the user keeps, build only the light appearance and list the dark states as "designed, not built" in the plan and report.
- Check the dark palette's contrast like the light one (the design audit's contrast rule applies to both) and raise design suggestions for dark pairs that fail.

## Build

- Components take colors from the theme only, so they switch with the appearance; never branch on dark mode inside a component for a color the theme can hold.
- Screens and previews/stories show both appearances when the design has both.

## Verify

Render each `-dark` state with the project's own dark switch, same viewport, DPR and seed as its light twin, and score it against its own reference. Per platform:

- **flutter:** pump with `MaterialApp(themeMode: ThemeMode.dark, theme: …, darkTheme: …)` or wrap in `MediaQuery(data: …copyWith(platformBrightness: Brightness.dark))`.
- **android-compose:** wrap content in the app theme with `darkTheme = true` (or `isSystemInDarkTheme` overridden through `LocalConfiguration` with `UI_MODE_NIGHT_YES`); for previews `@Preview(uiMode = UI_MODE_NIGHT_YES)`.
- **kmp-cmp:** the shared theme's dark flag in the common render, as Android on the host.
- **ios-swiftui:** `.preferredColorScheme(.dark)` or `.environment(\.colorScheme, .dark)` on the rendered view; for UI tests the scheme or launch environment the project uses.
- **react-native:** the project's theme provider in dark (or the `useColorScheme` mock the tests use).
- **web-react:** Playwright `colorScheme: "dark"` on the page for `prefers-color-scheme`, or set the project's class/attribute (`document.documentElement.classList.add("dark")`, `data-theme="dark"`) before capture.
- **web-html:** Playwright `colorScheme: "dark"`, or the site's theme class/attribute.

A dark state that was not built (plan kept light only) is `rendered: false` with the reason "dark theme not built (plan kept as is)".
