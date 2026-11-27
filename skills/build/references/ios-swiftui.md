# Build iOS SwiftUI

## Tokens
Reuse named asset colors, semantic fonts and existing design-system types. Add new values to the planned token files or asset sets. Use points and scalable text styles. Check whether vertical design coordinates are measured from the full viewport or from the safe area. Account for the top safe-area inset once, and confirm the generated layout on a simulator.

## Components
Build small View structs with explicit inputs and action closures. Use native controls so accessibility, focus and scaling work. Use leading/trailing alignment, and supply accessibility labels for icon actions. Keep existing API defaults intact.

## Previews and tests
Follow the project's deployment target and use #Preview or PreviewProvider with injected fixture state and theme. Exercise state transitions in the existing test target, and preview RTL with the appropriate locale and layoutDirection environment.

## Strings
Use the app's .xcstrings catalog or existing .strings/.stringsdict tables and bundle. Text with LocalizedStringKey and String(localized:) are valid localization entry points. Ensure every generated key actually appears in the planned table and use the correct resource bundle in Swift packages. Preserve format and plural variants. Record untranslated keys in todos.json.

## Assets
Add image and color sets in the existing catalog, with Contents.json and appearance/scale variants where appropriate. Reuse SF Symbols where the installed SDK and deployment target support them.

## State
Use the existing Observation, ObservableObject or TCA pattern with the app's ownership and injection conventions. Keep view state seedable for previews and verification.

## Folders
Add files to the owning Xcode target or SwiftPM target, respecting synchronized versus explicit Xcode groups. Follow existing feature and design-system folders.

## Checks
Use xcodebuild -list and -showdestinations with the actual project or workspace. Build the selected app scheme for an installed iOS simulator and run its configured tests on an available simulator. If the simulator runtime is missing but the simulator SDK is installed, compile the actual app target with xcodebuild -target <target> -sdk iphonesimulator and record that launch and device tests were unavailable. Use swift test only for a package and host-compatible tests. Add approved packages through SwiftPM using the project's existing configuration. Run lint_generated.py with --platform ios-swiftui and check catalog key coverage separately.

## Don't
Avoid hard-coded UI strings via Text(verbatim:) and view-local color literals. Avoid changing deployment targets, signing, or target-wide settings to make an individual component work.
