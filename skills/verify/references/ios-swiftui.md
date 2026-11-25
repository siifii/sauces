# Verify SwiftUI

## Render test
Prefer the existing snapshot runner when it can export actual PNGs. Otherwise add an XCTest file to an existing UI test target and seed it through the app's existing launch arguments or fixture mechanism. Wait for a stable accessibility identifier before capture. Capture the relevant view/window with XCUIElement.screenshot() and save each image as an XCTAttachment with a unique state name and lifetime .keepAlways.

Use the same simulator configuration, status-bar treatment, interface style, Dynamic Type and locale in both passes. Render RTL with the appropriate test plan language/region or existing injected locale and layout direction, and keep RTL captures separate from LTR scoring.

## Run
List schemes and simulator destinations. Run xcodebuild test with the discovered project/workspace, scheme, simulator UDID, -only-testing for the render test and a fresh -resultBundlePath inside the iteration directory. Run the installed `xcrun xcresulttool export attachments --help`, export from that bundle, and map exports by attachment name to <id>.png. Compile and lint the new test using the build reference. When the project has no runnable capture harness, test target or simulator, record why and use the manual checklist. Follow the build reference when a target-membership edit is needed and obtain plan approval before changing project configuration.
