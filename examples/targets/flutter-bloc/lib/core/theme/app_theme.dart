import 'package:flutter/material.dart';

import 'app_colors.dart';

abstract final class AppTheme {
  static const Color _seed = Color(0xFF3D5AFE);

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(seedColor: _seed);
    return ThemeData(
      useMaterial3: true,
      fontFamily: 'Inter',
      colorScheme: scheme,
      extensions: <ThemeExtension<dynamic>>[
        AppColors(surfaceMuted: scheme.surfaceContainerHighest),
      ],
    );
  }
}
