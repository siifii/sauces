# Build React Native

## Tokens
Reuse theme semantics, StyleSheet definitions, NativeWind configuration or the design-system package already in use. Add new values in the planned token module. Use logical layout directions and support text scaling.

## Components
Use functional components and follow the project's TypeScript or JavaScript conventions. Keep reusable components independent of navigation. Use Pressable or the existing buttons with accessibility roles, labels and state where needed. Preserve defaults when extending. Use platform variants only when the existing project or approved design requires a difference.

## Previews and tests
Use the configured Storybook or preview mechanism. Test default, loading and error states through props with the existing test setup. Use the project's established React Native Testing Library patterns when available. Check RTL with the supported language and on-device configuration.

## Strings
Use the existing translator and add keys to its actual message catalogs. Preserve placeholders and plurals, and record outstanding translations. With no runtime localization, keep copy in a typed feature-level messages module until the plan approves localization. Use start/end styling and verify native RTL configuration against the installed React Native or Expo version.

## Assets
Reuse the project's icon library and asset pipeline. Use static require/import for bundled raster files and preserve density variants. Use SVG tooling only when already configured or approved in the plan. Avoid adding a native dependency solely to replace an adequate built-in asset.

## State
Follow the existing hooks/store conventions. Keep the screen view seedable with data and callbacks; connect it to its route or container using the existing ownership and navigation API. Leave unknown business behavior as TODO(sauces).

## Folders
Preserve feature and design-system conventions. In Expo Router, keep screen entry files in the existing app directory and shared components outside that route tree. For bare React Native use the existing registered entry point and component roots.

## Checks
Use the lockfile’s package manager and run existing lint, typecheck and test scripts from the proper package or workspace. Use its installed compiler when no typecheck script exists and TypeScript is configured. For Expo, use the installed CLI to export bundles for configured mobile platforms and report this as a bundle check. For a bare app, build via the configured Gradle wrapper and Xcode workspace/scheme as available. Never report a host build based on a bundle check. Use `expo install` only for approved SDK dependencies or the existing package manager where appropriate. Run lint_generated.py with --platform react-native and review message-catalog coverage separately.

## Don't
Avoid introducing Expo into a bare app, changing routing libraries, running a destructive prebuild, or editing generated native hosts for a JS-only design change.
