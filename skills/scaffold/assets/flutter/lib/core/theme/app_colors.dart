import 'package:flutter/material.dart';

/// Design tokens that have no Material 3 [ColorScheme] role.
/// Add one field per token, and keep copyWith and lerp in step.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({required this.surfaceMuted});

  /// The brand color the Material 3 schemes are generated from. Sauces sets it
  /// from the design's primary color token when there is one.
  static const Color seed = Color({{seed}});

  final Color surfaceMuted;

  @override
  AppColors copyWith({Color? surfaceMuted}) =>
      AppColors(surfaceMuted: surfaceMuted ?? this.surfaceMuted);

  @override
  AppColors lerp(ThemeExtension<AppColors>? other, double t) {
    if (other is! AppColors) return this;
    return AppColors(
      surfaceMuted: Color.lerp(surfaceMuted, other.surfaceMuted, t)!,
    );
  }
}
