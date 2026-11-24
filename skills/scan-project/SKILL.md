---
name: scan-project
description: This skill should be used when the user asks to "scan the project", "detect the architecture", "inventory components", "find the theme and design tokens", "what UI toolkit does this app use", or runs "/sauces:scan-project". Profiles an Android Compose, iOS SwiftUI, KMP/CMP or Flutter project into .sauces/project-profile.json.
---

# Scan project

Scan the current repository and write `.sauces/project-profile.json`. Detect the platform(s) and UI toolkit from build files (`build.gradle(.kts)`, `Package.swift`/`.xcodeproj`, `pubspec.yaml`, KMP source sets), the architecture and state management, the theme/design-system location and existing tokens, the inventory of existing components (name, path, params, preview availability), conventions (folders, naming, localization and RTL, DI, navigation) and available screenshot-test tooling. Read files only; never modify the project during a scan. (Stub: implemented in Phase 2.)
