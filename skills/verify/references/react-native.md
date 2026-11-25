# Verify React Native

## Render test
Reuse a configured Maestro or Detox harness and launch the actual Expo or bare build. Seed each screen state with existing fixture routes, launch arguments or test data. Wait for the expected UI by accessibility label or test ID. Keep app state, target, device size, appearance, locale and font scale consistent between passes. Match device chrome to the reference and document any crop. Capture RTL on a device or simulator configured for the app’s RTL locale, keeping RTL output separate.

## Run
Run the existing test command for the specific flow. For Maestro use takeScreenshot with a unique state path and resolve the runner's actual artifacts directory. For Detox retain screenshots from the configured artifacts runner and map them to state IDs. With equivalent scripted navigation on a booted target, capture with `adb -s <serial> exec-out screencap -p` or `xcrun simctl io <udid> screenshot <path>`. Place each fresh <id>.png in the current iteration directory. Reuse identical host/configuration for the determinism check. Compile or parse test changes with the actual runner. If there is no runnable app, fixture state, device or capture harness, record the reason and use the manual checklist without assigning a score. JavaScript snapshots and web exports do not stand in for mobile captures.
