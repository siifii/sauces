import 'package:flutter/material.dart';

@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({required this.surfaceMuted});

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
