# Scaffold iOS SwiftUI

1. In the target root, run `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/scaffold_native.py" ios-swiftui --name "<display name>" --org "<reverse.domain>"`. This creates the bundled, versioned starter inside the selected destination and refuses to overwrite an existing path. Use the official IDE template only if the user requested a different template. If an IDE handoff is necessary, give the exact destination and resume only after the template exists.
2. Add Home and its seedable state inside the app target using the chosen structure. Use semantic colors in Assets.xcassets and a shared theme type for fonts and spacing; wrap a preview with representative state. Connect Home to the app's WindowGroup.
3. Use a target-member String Catalog for English and the chosen locales, preserving source as a fallback and recording missing translations. Check RTL in Preview or the simulator.
4. Discover the project scheme and simulator destinations with xcodebuild. Build the app for an installed iOS simulator and run the template tests when available. Record individual check results and add a Sauces scaffold README section with structure, locales and the build command.
