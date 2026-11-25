# Verify Compose Multiplatform

## Render test
Seed the real commonMain screen through a configured Android/iOS host or an existing compatible screenshot harness. Reuse common fixture state across hosts. Follow the Android or iOS verify reference for host capture and store files separately per host. Desktop captures can be useful for inspection when a desktop runner already exists; identify the runner explicitly.

## Run
Choose the reference's matching mobile host for scoring, based on its device chrome and dimensions; when unspecified choose an available mobile host and record it. Use the same host and configuration for both determinism passes. Keep additional host captures under .sauces/verify/ and report which hosts and RTL locales were exercised. Discover actual module tasks/schemes at runtime and lint test changes using the KMP build reference. Record missing hosts and render failures. Use the manual checklist when no compatible runner can capture the screen.
