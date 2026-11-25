# Scan SwiftUI

- Read the iOS Xcode project/workspace or Swift Package manifest. Inspect target membership (including synchronized groups), package products, deployment target, app entry point, and SwiftUI view files. Report Xcode schemes only when visible in shared metadata.
- Trace the root view, environment values and view modifiers. Record semantic theme types and the asset catalog or Swift files that define design tokens.
- Infer `mvvm` from a view model owning presentation state or `tca` from a ComposableArchitecture reducer and Store. Record `observation`, `observable-object`, `tca` or `local-state` only when used. Check environment injection and package wiring before naming a DI library.
- Inventory reusable View structs and their initializer parameters. Exclude the app entry point, screen-level destinations, previews and private views. Look for #Preview and PreviewProvider references to the component.
- Record `string-catalog` for .xcstrings, or `strings-ios` for .lproj .strings/.stringsdict. Read catalog sourceLanguage and localization keys, or enumerate the .lproj folders. Check direction handling and Arabic or Hebrew localizations.
- Identify actual SnapshotTesting imports, snapshot assertions or XCTest screenshot captures. Derive component structure from target files and source folders. Use common scan finding rules with the Swift lint rules and allow the actual token sources.
