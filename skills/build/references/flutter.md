# Flutter build rules

How to write UI a Flutter developer would merge without rewriting. `build` and the `component-builder` agent follow this file; `plan` reads it so items and recommendations agree with it. Checked against Flutter 3.41 (stable) on 2026-11-25. Where an API depends on the SDK version, the section says so: read the project's `pubspec.yaml` `environment.sdk` and `flutter --version` before relying on it.

Code samples use the flutter-bloc fixture's names (`AppButton`, `AppTextField`, `AppColors`, `context.l10n`). Use the project's real names.

## Tokens

- Colors come from the theme only: `Theme.of(context).colorScheme.<role>` for Material roles, `Theme.of(context).extension<AppColors>()!.<field>` for custom tokens. Never `Colors.*`, `Color(0x…)`, `Color.fromARGB`/`fromRGBO` in widget code. `Colors.transparent` is the one exception.
- Type comes from `Theme.of(context).textTheme.<style>`. Read the theme once per `build` (`final textTheme = Theme.of(context).textTheme;`).
- Map by meaning, not by hex: main button fill → `primary`, its label → `onPrimary`, body text → `onSurface`, secondary text and icons → `onSurfaceVariant`, field borders → `outline`, errors → `error`, page background → `surface`. The plan already chose the role for each design color; use the one in the item `notes`.
- **Never change an existing theme value or role** (`ColorScheme.fromSeed` arguments, an existing `TextTheme` entry, an existing component theme, an existing `ThemeExtension` field's value) unless the plan has a `theme` recommendation (`rec-design-theme-*`) whose `choice` is not `keep`. With `keep`, reused components render in the project's existing roles and styles. That difference is expected; verify reports it. Never "fix" it with per-widget overrides on a reused component.
- Additive tokens (`token` items) go where the project keeps tokens (`theme.tokens_source`), in the mechanism it already uses:
  - **A constants class** (`abstract final class AppColors { static const Color brand = Color(0xFF…); }`, `lib/core/constants/app_colors.dart`): add a `static const` in the same style and read it the way existing code does.
  - **flex_color_scheme, a generated tokens file, or another token system**: add the token the way that system does (its config, its source file, then its generator if it has one). Never introduce a new `ThemeExtension` architecture (or any new token mechanism) into a project that doesn't use one; that is a `theme` recommendation.
  - **A `ThemeExtension`** (the fixture's `AppColors`): as below.
  - A new color is a new field on the project's `ThemeExtension`: add the field, the constructor parameter, `copyWith`, and `lerp` (`Color.lerp(a, b, t)!`). Follow the existing fields' style (`required` like the others), and pass a value at every place the extension is constructed (grep for `AppColors(`: the light theme, the dark theme if any, tests). Those are theme files, so `lint_generated.py` allows the literal there. Existing fields and their values stay as they are.
  - A new text style only new components use is a field on a `ThemeExtension` when the project already uses theme extensions (for example a new `AppTextStyles` extension in the theme folder, registered in the theme's `extensions:` list) built from an existing `TextTheme` entry with `copyWith(...)`. Adding an extension to the `extensions:` list is additive; editing the existing entries is not.
  - Literal values (`Color(0xFF3D5AFE)`, font sizes) are allowed only in the project's token and theme files: the `theme/` folder, `theme.tokens_source`, and for the `atomic`/`layered` structures the `tokens` folder. The build skill passes those files to `lint_generated.py` as `--allow-colors` globs, which exempt them from the color rule only (string rules still apply); anywhere else a color literal is a finding.
- Design values a new component needs that the theme has no token for (sizes, gaps, radii): follow the project. If it writes them inline (`const SizedBox(height: 16)`, `BorderRadius.circular(12)`), write them inline in the same style. Don't invent a spacing system.
- Fidelity notes for Material 3 (apply only in new code or through a chosen recommendation):
  - M3 text styles carry letter spacing (body `+0.5`, label `+0.1`) and fixed heights. A design drawn in a browser with `letter-spacing: 0` matches better with `letterSpacing: 0` and the design's line height (`height: lineHeight / fontSize`, for example 36/28). Put those values in the additive text style, never per widget.
  - `OutlineInputBorder` draws the unfocused error border at 1 px. A 2 px design error border needs `errorBorder`/`focusedErrorBorder` with `BorderSide(width: 2, color: colorScheme.error)` in new code or an additive parameter; on a reused field that is an expected difference.
  - Golden text rendering (Skia) and browser text rendering differ slightly at glyph edges. That costs a little similarity; don't chase it with offsets.

## Components

- Every widget: a `const` constructor when every field is final and const-able, named parameters, `super.key` last (match the project's order if it differs), `final` fields, documentation comments on public parameters you add.
- `StatelessWidget` by default. `StatefulWidget` only for state that lives with the widget (a `TextEditingController`, an `AnimationController`, focus). Business state goes to the state-management layer (see State).
- Composition over inheritance: wrap or compose the project's widgets and Material widgets; never `extends AppButton` or `extends FilledButton`.
- Name new widgets the way the project does (`conventions.naming`), after their role (`AppLink`, `LoginHeader`), one public widget per file, file name in `snake_case` matching the class.
- Imports: follow the project. The fixture uses relative imports inside `lib/` and `package:` imports in `test/`.

### Reuse

Call the existing component with the parameters the plan item lists. Pass strings from l10n and nothing else.

### Extend (additive only)

An `extend` item names the exact parameter, type and default. Implement exactly that:

```dart
const AppButton({
  required this.label,
  required this.onPressed,
  this.loading = false,
  super.key,
});

/// Shows a progress indicator instead of the label and ignores taps,
/// keeping the enabled look. Defaults to false (the original behavior).
final bool loading;
```

- The new parameter is optional and its default reproduces today's output exactly. With the default, the widget tree is the same as before.
- Never remove, rename, reorder positional, or change the type or default of an existing parameter. Never change existing styling.
- Keep the diff minimal: add lines, change only the lines the new parameter must touch (the constructor, the one expression that uses it). Never reformat or reorder the rest of the file. Do not run `dart format` on a file you changed unless `dart format --output=none --set-exit-if-changed <file>` exited 0 on it before your edit.
- Existing call sites and the existing tests must keep passing unchanged. Add a test for the new behavior to the component's existing test file (append a `testWidgets`).
- A variant the design shows on a reused component that would need a non-additive change: leave the component alone, record the difference, and say so in the summary.

Extension patterns that keep old behavior:

- **Loading on a button.** Keep the enabled look (the design shows the fill, not the disabled style) and swallow taps: `onPressed: loading && onPressed != null ? () {} : onPressed`, `child: loading ? progress : Text(label)`. Give the progress indicator the label as its `Semantics(label: ...)` so screen readers still announce the button. A spinner drawn as a static arc in the design is a frame of the real indeterminate indicator: build `CircularProgressIndicator(strokeWidth: 2.5, strokeCap: StrokeCap.round, color: colorScheme.onPrimary)` inside a `SizedBox.square(dimension: 24)` with the design's size and stroke, not a frozen `value:`. Don't pass `year2023` (deprecated in 3.41; its default `true` already draws no track gap).
- **Trailing icon in a field.** `final Widget? suffixIcon;` passed to `InputDecoration(suffixIcon: suffixIcon)`. `null` is today's behavior.
- **Error text or helper text**: `String? errorText` / `helperText` passed to `InputDecoration`. Already present in many projects; check first.

### Previews and tests

Flutter has no stable, project-wide preview convention. Follow the project:

- The project uses Widgetbook: add a `@widgetbook.UseCase` for each new component, next to the existing ones.
- The project uses `@Preview` from `package:flutter/widget_previews.dart` (experimental; present in recent SDKs such as 3.41, API may change): add one per new component the same way. Never introduce it in a project that doesn't use it.
- Otherwise (the common case, and the flutter-bloc fixture): add one widget test per new widget and per screen, in the project's test layout (`test/<same path as lib>/<file>_test.dart`), using the project's test helper (`tester.pumpApp(...)`). A screen test pumps each design state by providing a seeded state (see State).
- Test strings through l10n, never as literals in widget arguments: `final l10n = lookupAppLocalizations(const Locale('en'));` then `find.text(l10n.loginTitle)`. Recorded test files are linted too.
- A screen with an indeterminate progress indicator never settles: use `tester.pump()`, not `pumpAndSettle()`, in its loading test.

## Strings & RTL

### Strings

- Every user-facing text goes through the project's localization: with ARB, `context.l10n.<key>` (or the project's accessor, such as `AppLocalizations.of(context)!.<key>`). Accessibility labels and tooltips the design doesn't show (`Show password`, `Hide password`) are strings too: add keys for them.
- Use the plan's `strings[]` keys and values exactly. A key the plan marked as existing is reused, not duplicated.
- New keys go into **every** ARB file in `arb-dir`:
  - the template (source) locale gets the value and an `@key` entry with a `description` that says where the text appears;
  - every other locale gets the **source value** and `"@key": {"description": "TODO(sauces): translate"}`. For a plain LTR fallback in an RTL catalog, wrap the value in LRI (JSON `\u2066`) and PDI (JSON `\u2069`) so neutral punctuation stays at the end of the phrase. Keep the source catalog unchanged. For ICU select/plural messages, isolate the displayed branch text without wrapping ICU syntax. Keep placeholders intact and verify the fallback visually. Never invent a translation.
- Insert entries next to the feature's other keys, or at the end, keeping the file's existing formatting (indentation, compact or expanded `@key` objects). Never rewrite or reorder existing entries. The ARB must stay valid JSON.
- Text that varies uses ICU, never concatenation or interpolation in Dart:
  - placeholders: `"loginWelcomeUser": "Welcome back, {name}"` with `"@loginWelcomeUser": {"placeholders": {"name": {"type": "String"}}}`;
  - plurals: `"{count, plural, =0{No messages} =1{1 message} other{{count} messages}}"` with an `int` placeholder. Copy the plural forms the source locale needs into other locales; the translator adds the rest (Arabic has `zero`, `one`, `two`, `few`, `many`, `other`).
- Regenerate after editing ARB files: `flutter gen-l10n` when `l10n.yaml` exists or `generate: true` is set. Fix any error it prints before going on. The output folder (`output-dir`) is generated: never edit it by hand.
- Keep the project's existing import path for the generated class. Recent Flutter versions deprecated the synthetic `package:flutter_gen/gen_l10n/...` package in favour of output inside the source tree (`output-dir`, for example `lib/l10n/gen/`). Don't migrate a project from one to the other; that is the user's decision. Whether `flutter pub get` still regenerates the localizations implicitly depends on the Flutter version and on `generate: true`, so run `flutter gen-l10n` explicitly. If it prints a deprecation warning, report it in the summary instead of acting on it.
- **Other localization stacks** (`easy_localization` JSON/YAML, `slang`, `intl_utils`'s `flutter_intl`): follow the project's mechanism: add keys to the files it already uses, in every locale, call strings the way existing code does (`'login.title'.tr()`, `t.login.title`, `S.of(context).loginTitle`), and run its code generator if it has one (`dart run slang`, `flutter pub run intl_utils:generate`). Never add `flutter gen-l10n`/ARB alongside it. If you are unsure how the project's stack works, ask.
- **Without localization** (`localization.system: none`, and the user did not choose the `localize` recommendation): one strings class per feature, `<feature>_strings.dart` (the lint allows that file name). Put it in the feature's folder per the profile and the chosen structure, beside the screen's folder (for example `lib/features/login/login_strings.dart`, or the screen's own folder in a layer-first project):

  ```dart
  abstract final class LoginStrings {
    static const title = 'Welcome back';
    static const showPassword = 'Show password';
  }
  ```

  `abstract final class` needs Dart ≥ 3.0 (check `environment.sdk`). On older SDKs write `class LoginStrings { LoginStrings._(); static const title = ...; }`. Widgets, `Semantics` labels and tooltips read `LoginStrings.title`, and tests find text with `find.text(LoginStrings.title)`, never with a literal.

### RTL

- Padding: `EdgeInsetsDirectional` (`.only(start:, end:)`, `.fromSTEB`), never `EdgeInsets.only(left:/right:)` or `fromLTRB` with different left/right values. `EdgeInsets.all`/`symmetric` are direction-neutral and fine.
- Alignment: `AlignmentDirectional.centerEnd`, `Alignment.center`; never `Alignment.centerLeft/Right`. Text: `TextAlign.start/end`, never `left/right`. Positioning: `PositionedDirectional`, `BorderRadiusDirectional` when corners differ.
- `Row` children follow the text direction automatically; don't reverse them by hand.
- Directional icons (back/forward arrows, chevrons, "next") mirror: `Icon(Icons.arrow_forward, matchTextDirection: true)` or the `Icons.adaptive.*`/`*_ios` variants the project uses. Non-directional icons (eye, search, check, close) never mirror.
- A "right-aligned" element in the design is end-aligned in code.

## Assets

- SVG icons render with `flutter_svg` (`SvgPicture.asset('assets/icons/eye.svg', colorFilter: ColorFilter.mode(colorScheme.onSurfaceVariant, BlendMode.srcIn), semanticsLabel: l10n...)`) only when `flutter_svg` is already in `pubspec.yaml` or the plan's approved `dependency_changes` lists it. Then add the package with `flutter pub add flutter_svg:<version from the plan>`.
- When it is not approved: put the SVG in `assets/icons/`, declare `assets/icons/` under `flutter: assets:` in `pubspec.yaml`, render the planned nearest Material icon (`Icons.visibility_outlined` / `Icons.visibility_off_outlined` for an eye toggle) and mark the usage `// TODO(sauces): render assets/icons/eye.svg with flutter_svg once approved`. If the plan simply mapped the icon to a Material icon (no asset item), use the icon and don't copy the SVG. Never add a package that isn't in `dependency_changes`.
- Raster images go in resolution folders: `assets/images/login_hero.png` (1.0x), `assets/images/2.0x/login_hero.png`, `assets/images/3.0x/login_hero.png`; declare `assets/images/` once and reference the 1.0x path. Export the variants from the source when it has the resolution; don't upscale a 1x image to fake 3x (say which variants are missing in a TODO).
- If the project has an asset constants class or `flutter_gen`, add the new asset there and use it; otherwise reference the path the way the project does.
- Fonts: use the project's bundled family through the theme. Never add `google_fonts` or a new font family without approval.

## Accessibility

- Labels come from l10n: `IconButton(tooltip: l10n.loginShowPassword, ...)` (the tooltip doubles as the semantics label), `Semantics(label: ...)` around custom controls, `semanticLabel:` on informative images and icons, `excludeSemantics`/`ExcludeSemantics` for decoration.
- Touch targets are at least 48 × 48 dp. `IconButton` and Material buttons give this by default; don't shrink them below it (`MaterialTapTargetSize.shrinkWrap` with a small `minimumSize`) without restoring the hit area.
- **Small text links next to other controls** (for example a 20 px "Forgot password?" row): keep the visual row and grow the hit area by turning the design's surrounding gaps into the button's padding, so nothing moves:

  ```dart
  Align(
    alignment: AlignmentDirectional.centerEnd,
    child: TextButton(
      onPressed: cubit.forgotPassword,
      style: TextButton.styleFrom(
        // The 8 px gap above and 20 of the 24 px gap below become padding:
        // the text stays where the design puts it and the hit area is 48 dp.
        padding: const EdgeInsetsDirectional.only(top: 8, bottom: 20),
        minimumSize: const Size(48, 48),
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
      ),
      child: Text(l10n.loginForgotPassword),
    ),
  ),
  const SizedBox(height: 4), // what is left of the 24 px gap
  ```

  Trade-off: the ink splash is off-centre vertically (it fills the 48 dp box, the text sits near its top). `MaterialTapTargetSize.padded` alone would also give 48 dp, but it grows the layout box around the centred text and pushes everything below down (by 14 px for a 20 px row with the default visual density; a denser `visualDensity` in the theme changes that). When the gaps around the link add up to less than 28 px, there is no room: keep the visual row, use `padded`, and record the layout difference in the summary.
- Text scales: never put text in a fixed-height container (`SizedBox(height: 20, child: Text(...))`) or set `textScaler`. Use `minimumSize`/`ConstrainedBox(minHeight:)` instead of fixed heights for controls with text. Screens scroll (`SingleChildScrollView` or a `ListView`) so 200% text and the keyboard don't overflow.
- Errors are text, not only color: show the message (`errorText`) with the colored border.
- Inputs: give fields the right `keyboardType`, `textInputAction` and `autofillHints` when the component supports them (or when the plan's `extend` item adds them). Don't extend a component for them beyond what the plan names: mention it in the summary instead.
- Contrast and target-size changes the design itself needs are design suggestions; apply them only when the plan's suggestion has `choice: "apply"`.

## State

Follow `state_management` from the profile. Put state next to the screen the way the project does it.

### BLoC / Cubit (`bloc`)

- `lib/features/<f>/cubit/<f>_cubit.dart` and `<f>_state.dart` (match the project: a `bloc/` folder with events for `Bloc` projects, `part`/`part of` if it uses that, `equatable` or `freezed` only if the project already depends on it; otherwise hand-written `==`/`hashCode` like the fixture's `HomeState`).
- An immutable state: `@immutable`, `final` fields, a `const` constructor with defaults, `copyWith`, value equality. A screen with a form and a submit:

  ```dart
  enum LoginStatus { initial, loading, failure, success }

  @immutable
  class LoginState {
    const LoginState({
      this.status = LoginStatus.initial,
      this.email = '',
      this.password = '',
      this.obscurePassword = true,
    });
    // final fields, copyWith, ==, hashCode
  }
  ```

- The Cubit takes an optional initial state so tests and verify can seed any design state: `LoginCubit({LoginState initialState = const LoginState()}) : super(initialState);`.
- Input methods ignore no-op updates (`if (email == state.email) return;`) and clear a failure when the user edits.
- Unknown behavior is a TODO, never a guess or a fake: no `Future.delayed`, no hard-coded credentials, no success after a timer.

  ```dart
  Future<void> submit() async {
    if (state.status == LoginStatus.loading) return;
    emit(state.copyWith(status: LoginStatus.loading));
    // TODO(sauces): call your auth repository with state.email and state.password, then emit LoginStatus.success or LoginStatus.failure.
  }
  ```

  Navigation (`forgotPassword`, after success) is a method with a `// TODO(sauces): …` body, or a callback parameter on the page if the project navigates from pages.
- The page provides the Cubit and a public view consumes it, so a test can provide a seeded Cubit:

  ```dart
  class LoginPage extends StatelessWidget {
    const LoginPage({super.key});
    @override
    Widget build(BuildContext context) =>
        BlocProvider(create: (_) => LoginCubit(), child: const LoginView());
  }
  ```

  `LoginView` builds from `BlocBuilder<LoginCubit, LoginState>`; every design state is a function of the state (`status == failure` → the error text, `loading` → the button's loading variant). A view that owns `TextEditingController`s is a `StatefulWidget`: create them in `initState` from the Cubit's current state (`TextEditingController(text: cubit.state.email)`), forward changes to the Cubit, dispose them.
- DI: if the project injects repositories (`get_it`, `RepositoryProvider`), leave the repository parameter out and say so in the submit TODO; don't create a fake repository.

### Other patterns

Every pattern needs the same contract as the Cubit: **each design state can be shown by seeding the state**, because tests and verify pump every state that way.

- `riverpod` (Riverpod ≥ 2.0 for `Notifier`; checked against the 3.x changelog): a `Notifier` whose initial state can be injected, a `ConsumerWidget`/`ConsumerStatefulWidget` screen, and a seeded override in tests:

  ```dart
  class LoginNotifier extends Notifier<LoginState> {
    LoginNotifier([this._initial = const LoginState()]);
    final LoginState _initial;
    @override
    LoginState build() => _initial;
    // emailChanged, submit (TODO(sauces)), ...
  }

  final loginProvider = NotifierProvider<LoginNotifier, LoginState>(LoginNotifier.new);

  // test / golden:
  ProviderScope(
    overrides: [
      loginProvider.overrideWith(
        () => LoginNotifier(const LoginState(status: LoginStatus.failure)),
      ),
    ],
    child: const LoginPage(),
  )
  ```

  Version notes: `overrideWith(() => notifier)` on a `NotifierProvider` works in 2.x and 3.x. Riverpod 3.0 (2025-09-10) added `overrideWithBuild` (replaces only `build`) and `ProviderContainer.test()`, and moved `StateNotifierProvider`/`StateProvider` to the legacy import, so don't write new `StateNotifier` code. Use codegen only if the project already does.
  - **autoDispose** (use it when the project's feature providers are auto-disposed): in 3.x, `NotifierProvider.autoDispose<LoginNotifier, LoginState>(LoginNotifier.new)` with the plain `Notifier` above. In 2.x the class must `extends AutoDisposeNotifier<LoginState>` and the provider is `NotifierProvider.autoDispose(...)` (alias `AutoDisposeNotifierProvider`). Using a plain `Notifier` with an autoDispose provider is a compile error in 2.x.
  - **Codegen** (`riverpod_generator`, `@riverpod class LoginNotifier extends _$LoginNotifier`): the generated provider is overridden the same way. Functional providers take `Ref ref` in 3.x; 2.x generated a per-provider ref type (`LoginRepositoryRef ref`). Copy the signature style of the project's existing providers. The generated provider's name differs by version too: 3.x drops the `Notifier` suffix (`LoginNotifier` → `loginProvider`), 2.x kept it (`loginNotifierProvider`). Read the generated `.g.dart` (after `dart run build_runner build`) rather than guessing the name.
- `provider`: a `ChangeNotifier` controller with private fields, getters and an optional initial state (`LoginController({LoginState initialState = const LoginState()})`). The page provides it (`ChangeNotifierProvider(create: (_) => LoginController(), child: const LoginView())`), and a public `LoginView` reads it with `context.watch<LoginController>()`. Tests seed it with `ChangeNotifierProvider(create: (_) => LoginController(initialState: ...), child: const LoginView())`.
- `setstate`: keep the state in the screen's `State` class. For seeding, give the screen an optional `@visibleForTesting` initial-state parameter (`LoginPage({super.key, this.initialState = const LoginState()})`).
- Anything else: follow the nearest existing feature; if there is none, ask.

## Folders

- Every file goes where its plan item's `path` says. The path already follows the chosen structure (`plan.json` `structure.choice`) and the item's `layer` (`${CLAUDE_PLUGIN_ROOT}/skills/plan/references/design-system-patterns.md`). Never move or rename an existing file to fit a pattern.
- Files the plan does not list as items:
  - state management beside the screen: `lib/features/<f>/cubit/` (or `bloc/`, `providers/`, `controllers/`, `notifiers/`, as the project does it), next to the screen's `view/` folder;
  - the feature strings class `<feature>_strings.dart` when the project has no localization (Strings & RTL);
  - tests in `test/`, mirroring the `lib/` path;
  - assets in the project's asset folder; generated l10n in its output folder.
  Nothing else: a helper widget the screen needs but the plan didn't list goes into the screen's file as a private class, or is raised in the summary.
- Feature folders follow `conventions.feature_folders` (the fixture: `lib/features/<f>/{cubit,view}`).
- Never write outside the project root or into `build/`, `.dart_tool/` or the platform host folders.
- **A project Sauces scaffolded** (its `root` is in `state.json` `generated_files`, and `lib/app.dart` has `home: const HomePage()` from the starter): point `home:` at the first `screen` item you build, and in `test/app_test.dart` replace `HomePage` (and its import) with that screen in both tests, providing whatever the screen needs the way its own screen test does. Leave the starter `home_page.dart` and its `homePlaceholder` strings in place, and mention in the summary that they can be deleted.

## Don't

- Hard-code colors (`Colors.*`, `Color(0x…)`) or user-facing strings in widget code, tests included.
- Edit, reorder, rename or delete an existing component's parameters, defaults or styling; reformat a file you only extended.
- Change an existing theme value or role without a chosen `theme` recommendation.
- Invent translations; skip a locale; edit the generated l10n output.
- Use `EdgeInsets.only(left:/right:)`, `Alignment.centerLeft/Right`, `TextAlign.left/right`.
- Add a package not in the approved `dependency_changes` (`flutter_svg`, `google_fonts`, `equatable`, `go_router`…).
- Fake behavior: delays, stub success, hard-coded credentials, invented navigation routes.
- Put text in fixed-height boxes, shrink tap targets below 48 dp, or use `pumpAndSettle` with an indeterminate spinner.
- Use `print`/`debugPrint` in UI code, `!` on nullable values you could handle, or `BuildContext` across async gaps without a `mounted` check.
