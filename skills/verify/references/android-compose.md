# Verify Android Compose

## Render test
Reuse the configured screenshot runner first. Render the actual screen in its app theme with fixture state for every design state. Set deterministic time/data, size, density, font scale and appearance. Render RTL using an existing RTL locale or a controlled RTL layout-direction provider; save those PNGs separately from the LTR scoring input.

For an existing instrumentation setup, capture the tagged screen node with Compose test captureToImage on a supported API and write PNG bytes into the test target's app-private files directory. Use a debug variant and pull each output via `adb -s <serial> exec-out run-as <applicationId> cat files/<id>.png` into the iteration directory. Resolve the installed application ID (including variant suffix) and test runner from the project. Use a preview or screenshot plugin only if it captures the required layout and state with the installed toolchain.

## Run
Discover the module and variant from Gradle. Run the relevant screenshot task or `./gradlew :<module>:connected<Variant>AndroidTest -Pandroid.testInstrumentationRunnerArguments.class=<test-class>` on the selected device. Remove or replace the exact prior PNGs before each run and validate every copied PNG. Run build lint on the test and compile it with the test runner. If capture or device is unavailable, record the reason and use the manual checklist. Lint or assembly alone cannot provide a fidelity score.
