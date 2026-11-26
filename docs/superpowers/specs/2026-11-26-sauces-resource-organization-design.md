# Sauces resource organization and naming

Date: 2026-11-26. Status: design approved in chat; awaiting spec review.

## 1. Intent

Make Sauces' own resources easier to find and extend, while keeping its Claude
Code plugin layout, generated target fixtures, and existing tool references
stable. Apply official conventions where the relevant ecosystem publishes them;
otherwise follow the target project's existing patterns instead of imposing a
universal naming rule.

## 2. Current state

The repository already uses the expected plugin roots: `.claude-plugin/`,
`agents/`, `assets/`, `docs/`, `examples/`, `scripts/`, `skills/`, and `tests/`.
Skills keep their `SKILL.md`, references, and supporting assets together.
Platform references and scaffold assets are already grouped by target platform.
Names such as `component-builder`, `scan-project`, and
`web-react-vite` are descriptive and consistent with their roles.

The main hygiene issue is generated output under `examples/targets/`: local
Gradle, Flutter, and React Native caches and build products account for about
one gigabyte and are not source fixtures. The existing root `.gitignore` does
not explicitly describe these target-specific generated directories.

## 3. Goals and non-goals

### Goals

- Document the repository's resource map and naming rules in contributor
  guidance.
- Preserve Claude Code's plugin discovery paths and the resource paths already
  used by skills, tests, and docs.
- Explicitly ignore and remove only confirmed generated/cache directories under
  `examples/targets/`.
- Verify that source fixtures remain tracked and generated outputs are not
  accidentally committed.

### Non-goals

- Move the plugin's root component directories into a new umbrella directory.
- Mass-rename valid files or change published skill/agent/platform identifiers.
- Delete fixture source, platform wrappers, IDE configuration, or user changes.
- Change the plugin's runtime behavior or generated target-project architecture.

## 4. Organization and naming rules

Keep the existing root layout:

```text
.claude-plugin/    plugin manifest and marketplace metadata
agents/            plugin agent definitions
assets/            plugin-wide assets
docs/              product docs and dated design/implementation records
examples/
  designs/<id>/    source design fixtures and their descriptions
  targets/<id>/    sample target projects
scripts/           standalone plugin-side helper programs
skills/<skill>/    SKILL.md, references/, and skill-specific assets/
tests/             script, skill, and fixture tests
```

Apply these conventions by resource type:

- **Claude Code plugin:** keep `.claude-plugin/plugin.json` at its required
  path and component directories at the plugin root. Keep each skill in a
  same-named directory with `SKILL.md`; put supporting knowledge in
  `references/` and templates/data in `assets/`. Use kebab-case for plugin
  component, skill, agent, and Markdown resource names. Preserve required
  filenames such as `SKILL.md` and `plugin.json`.
- **Platform IDs and fixture names:** retain the canonical platform IDs used
  across schemas, references, and target fixtures. When multiple fixtures
  represent one platform, add a meaningful variant, such as `flutter-bloc` or
  `web-react-vite`. Do not rename an ID without updating its consumers in the
  same change.
- **Language-specific source:** use that language's official convention rather
  than applying plugin Markdown naming to code. Python modules remain
  lowercase `snake_case`; Dart files and directories use
  `lowercase_with_underscores`; Kotlin source follows package paths and
  Kotlin's class/file naming guidance. Keep tests in the existing Python
  `test_*.py` style.
- **Target resources:** preserve the target ecosystem's resource paths.
  Android uses typed `res/` directories and configuration qualifiers; Flutter
  declares asset paths in `pubspec.yaml`; Swift package resources remain scoped
  to their target; Compose Multiplatform uses source-set `composeResources`
  folders organized by resource type. For React Native and web, follow the
  existing target repo/framework convention because there is no single
  universal resource directory or file-naming rule.
- **Design fixtures:** keep each design in `examples/designs/<design-id>/`
  with its description and source inputs together. Preserve current
  `screen--state` names; use `<screen>@<width>--<state>` only for the responsive
  web sample as specified in the web-target design.
- **Documentation:** retain the canonical `docs/superpowers/spec.md` and
  `plan.md`; dated specs and plans use `YYYY-MM-DD-<topic>.md` in their
  respective `specs/` and `plans/` folders.

Official references:

- [Claude plugin structure and testing](https://claude.com/docs/plugins/build)
  documents the manifest location, root component directories, and per-skill
  `references/` and `assets/`.
- [Anthropic's plugin-structure skill](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/plugin-structure/SKILL.md)
  recommends kebab-case component and support-file names.
- [PEP 8](https://peps.python.org/pep-0008/) recommends short lowercase Python
  module names and permits underscores when they improve readability.
- [Effective Dart](https://dart.dev/effective-dart/style) specifies
  `lowercase_with_underscores` for packages, directories, and source files.
- [Android app resources](https://developer.android.com/guide/topics/resources/providing-resources)
  specifies typed resource directories and configuration-qualified variants.
- [Kotlin coding conventions](https://kotlinlang.org/docs/coding-conventions.html)
  describes package-matching source paths and Kotlin source-file naming.
- [Compose Multiplatform resources](https://kotlinlang.org/docs/multiplatform/compose-multiplatform-resources-setup.html)
  specifies `composeResources` and type directories such as `drawable`, `font`,
  `values`, and `files`.
- [Apple: bundling resources with a Swift package](https://developer.apple.com/documentation/xcode/bundling-resources-with-a-swift-package)
  scopes resources to a target and presents `Sources/<Target>/Resources` as an
  optional organizing subdirectory.
- [React Native images](https://reactnative.dev/docs/images) supports static
  assets referenced from the source tree and does not prescribe one shared
  asset directory.

## 5. Generated target artifacts

Add explicit root ignore patterns for generated/cache directories that occur
inside sample target projects, including:

- `.gradle/`, `.kotlin/`, and `build/`
- `.dart_tool/`
- `node_modules/`, `.expo/`, and `dist/`
- `ios/Flutter/ephemeral/`
- `.next/` for the planned Next.js fixture

Before removing anything, confirm each resolved path is inside
`examples/targets/`, ignored by Git, and is one of these generated/cache
directories. Remove only those exact directories. Preserve tracked source and
fixture configuration, `.idea/`, generated platform wrapper files, generated
host source, and all unrelated ignored or untracked files.

Do not delete or rewrite any of the current uncommitted changes. If a target
directory contains unexpected untracked source or an artifact that cannot be
identified confidently, leave it in place and report it rather than broadening
the cleanup.

## 6. Documentation changes

- Add a concise resource map and naming guidance to `CLAUDE.md`, including the
  plugin-vs-target distinction and the official references above.
- Keep the development layout in `README.md` aligned with the actual root
  structure and example fixture naming.
- Update `.gitignore` with explicit generated-target patterns.

Do not create a second standalone naming policy if these two contributor
documents can link to or summarize the same rules without duplication.

## 7. Validation and acceptance

- Confirm plugin discovery paths and skill/reference/asset locations are
  unchanged.
- Confirm tracked source fixture counts and source files are unchanged by the
  cleanup.
- Confirm the selected cache/build directories are ignored and absent after
  cleanup; do not require platform SDKs to be installed to recreate them.
- Run the repository's default pytest suite and `claude plugin validate
  .claude-plugin/plugin.json`.
- Review `git status` and the final diff to ensure only the intended docs,
  ignore rules, and explicitly selected generated directories are affected.
