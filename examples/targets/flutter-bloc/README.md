# flutter-bloc fixture

Sample Flutter app used as the "existing project" target for Sauces tests. Package `fixture_app`: Flutter 3.41, BLoC (`flutter_bloc`), ARB localization (`en`, `ar`), Material 3 theme seeded from `#3D5AFE` with an `AppColors` theme extension, Inter bundled under `assets/fonts/`.

Generated localizations (`lib/l10n/gen/`) are not committed; `flutter pub get` regenerates them.

## The deliberate gap

`lib/core/widgets/app_card.dart` uses `Color(0xFFEEEEEE)` directly instead of a theme color (`AppColors.surfaceMuted`). It is the only hard-coded value in `lib/` outside `lib/core/theme/`, and the one `colors` finding a scan of this project should report.
