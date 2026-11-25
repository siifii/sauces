# Verify: Flutter

How to render Flutter screens for scoring. Rendering uses plain `flutter_test` (no new dependency), with a capture-only test that Sauces owns under `test/sauces/`.

## Why capture-only, not `matchesGoldenFile`

Golden files committed to the user's tests fail on other machines (font rasterization differs between macOS, Linux and CI) and after every intended UI change. Sauces' test therefore never compares anything. It pumps every design state, fails only on exceptions and layout overflows, and writes PNGs only when `--dart-define=SAUCES_RENDER_DIR=<dir>` is set. Without the define it is a fast smoke test that keeps passing in the user's `flutter test`.

If the project already has golden tooling (`golden_toolkit`, `alchemist`, its own `matchesGoldenFile` tests; the profile's `screenshot_tooling`), still use this capture test for scoring, and mention in the summary that the project's goldens may need `--update-goldens` after the build.

## The render test

Write one file per screen: `test/sauces/<screen>_render_test.dart` (snake_case screen id). Copy the project's test setup instead of importing app internals you don't need:

- The `MaterialApp` arguments the project's pump helper uses (theme, `localizationsDelegates`, `supportedLocales`), plus `debugShowCheckedModeBanner: false`. Don't edit the user's helper. Read `lib/app.dart` (or wherever `MaterialApp` is built) too, and use its `theme`, `darkTheme` and `themeMode` if the helper leaves them out.
- `home:`: if the screen widget builds its own `Scaffold`, pass it directly; otherwise wrap it in `Scaffold(body: ...)` the way the helper does.
- Seed each design state through the screen's state hook (build reference, State section). For BLoC, provide a seeded Cubit to the public view: `BlocProvider(create: (_) => LoginCubit(initialState: ...), child: const LoginView())`. Placeholder field values the design shows (`alex@example.com`, a password) are test data: put them in the seeded state, never in app code.

```dart
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
// + the app's theme, l10n and the screen's view/cubit/state imports

const _renderDir = String.fromEnvironment('SAUCES_RENDER_DIR');

/// Real fonts from the app's FontManifest (bundled families + MaterialIcons);
/// without this, tests render the Ahem block font.
Future<void> _loadFonts() async {
  final manifest =
      json.decode(await rootBundle.loadString('FontManifest.json')) as List<dynamic>;
  for (final entry in manifest.cast<Map<String, dynamic>>()) {
    final loader = FontLoader(entry['family'] as String);
    for (final font in (entry['fonts'] as List<dynamic>).cast<Map<String, dynamic>>()) {
      loader.addFont(rootBundle.load(font['asset'] as String));
    }
    await loader.load();
  }
}

Future<void> _render(
  WidgetTester tester,
  Widget screen,
  String name, {
  Locale locale = const Locale('en'),
}) async {
  tester.view.physicalSize = const Size(780, 1688); // reference PNG size
  tester.view.devicePixelRatio = 2; // reference scale
  addTearDown(tester.view.reset);
  debugDisableShadows = false; // render real elevation shadows
  try {
    await tester.pumpWidget(
      MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        locale: locale,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(body: screen),
      ),
    );
    // Fixed pumps, not pumpAndSettle: spinners animate forever.
    await tester.pump();
    await tester.pump(const Duration(seconds: 1));
    expect(tester.takeException(), isNull);
    if (_renderDir.isEmpty) return;
    final element = find.byType(MaterialApp).evaluate().single;
    await tester.runAsync(() async {
      final image = await captureImage(element);
      final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      final file = File('$_renderDir/$name.png');
      file.parent.createSync(recursive: true);
      file.writeAsBytesSync(bytes!.buffer.asUint8List());
    });
  } finally {
    debugDisableShadows = true; // flutter_test checks debug flags are restored
  }
}

Widget _login(LoginState state) => BlocProvider(
      create: (_) => LoginCubit(initialState: state),
      child: const LoginView(),
    );

const _filled = LoginState(email: 'alex@example.com', password: 'password');

void main() {
  setUpAll(_loadFonts);

  testWidgets('login default', (t) => _render(t, _login(_filled), 'login--default'));
  testWidgets(
    'login error',
    (t) => _render(t, _login(_filled.copyWith(status: LoginStatus.failure)), 'login--error'),
  );
  testWidgets(
    'login loading',
    (t) => _render(t, _login(_filled.copyWith(status: LoginStatus.loading)), 'login--loading'),
  );
  testWidgets(
    'login default rtl',
    (t) => _render(t, _login(_filled), 'login--default--rtl', locale: const Locale('ar')),
  );
}
```

Adapt it, don't paste it blind:

- Size: `physicalSize` is the reference PNG's pixel size and `devicePixelRatio` the design's scale (the manifest state's `layout`, or `reference width / logical width`; 2 for the sample design). When the design's logical width is unknown, use 2 and say so.
- The PNG `name` is exactly the state's id, `<screen>--<state>`, and `<screen>--<state>--rtl` for the RTL pass.
- One RTL test per design state when the project has a right-to-left locale (the profile's `localization.locales`: `ar`, `he`, `fa`, `ur`). Without one, wrap the screen in `Directionality(textDirection: TextDirection.rtl, child: ...)` and say in the summary that the RTL pass used the source strings.
- Riverpod, Provider, setState: seed through the hook the build reference describes (`ProviderScope(overrides: ...)`, `ChangeNotifierProvider(create: ...)`, `initialState:`).
- Images from the network can't load in tests. If the screen shows one, note it in `remaining` instead of faking it.
- Keep it lint-clean (`lint_generated.py`): no color literals, and no UI copy as literals. Labels come from l10n through the real widgets; only test data such as placeholder field values is written in the test.

## Run

From the project root, with an absolute render folder (paths may contain spaces, so keep the quotes):

```bash
flutter test --dart-define="SAUCES_RENDER_DIR=$PWD/.sauces/verify/_render" test/sauces/
```

- Exit 0: every PNG is in `.sauces/verify/_render/`.
- A failing LTR test: read the error. A compile error or exception in the test itself is yours to fix (wrong import, wrong seed). A layout overflow (`A RenderFlex overflowed by …`) is a real bug in the built screen: fix it as a build fix (iteration counts).
- A failing RTL test only: record each overflow or exception in that state's `rtl_issues` (with the widget and pixel amount from the message) and continue; the PNG may still have been written.
- `flutter` missing, or the tests can't compile after two honest attempts: rendering failed (`rendered: false`, manual checklist).

Run `python3 -I "${CLAUDE_PLUGIN_ROOT}/scripts/lint_generated.py" --platform flutter test/sauces/<screen>_render_test.dart` and `flutter analyze --no-fatal-infos test/sauces/` on the file, and fix what they report.

## RTL check

Beyond overflows, compare `rtl.png` with the LTR render and check the code. Record each issue as one sentence in `rtl_issues`:

- Elements that should mirror and didn't (a trailing link still on the right, a leading icon still on the left, text aligned left).
- In the files build created or changed: `EdgeInsets.only(left:/right:)`, `EdgeInsets.fromLTRB` with unequal sides, `Alignment.centerLeft/centerRight`, `TextAlign.left/right`, `Positioned(left:/right:)` instead of the directional forms, and directional icons (arrows, chevrons) without `matchTextDirection: true`.
- Text that is clipped or truncated (ellipsis) only in RTL.

Glyph boxes ("tofu") are expected when the bundled fonts have no glyphs for the RTL script (Inter has no Arabic). They are not an issue. Mention once in the summary that the RTL render checks layout, not glyph shapes.

## Expected differences (don't fix)

- Text antialiasing and subpixel positioning: Flutter's test renderer and the design tool rasterize text differently. A few points of score lost to soft edges around text is normal.
- Placeholder content the design marks as placeholder (field values, avatars, sample names).
- Theme values the plan kept (item `notes`, recommendations left at `keep`), for example a seeded `ColorScheme` whose surface is tinted while the design is white.
- Fonts the project doesn't bundle. If the design uses a family not in `FontManifest.json`, the render falls back. Report it; adding a font is a plan decision.
- Shapes drawn differently by Material widgets (for example the `CircularProgressIndicator` arc length at a given frame).
