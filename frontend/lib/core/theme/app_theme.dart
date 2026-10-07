import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Tokens de color extraídos del diseño.
class AppColors {
  const AppColors._();

  static const background = Color(0xFFFBF7F0);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceMuted = Color(0xFFF1EDE6);
  static const espresso = Color(0xFF2B1710);
  static const terracotta = Color(0xFFA24B2B);
  static const terracottaSoft = Color(0xFFF6DDD3);
  static const textPrimary = Color(0xFF1F1410);
  static const textMuted = Color(0xFF7A6B63);
  static const success = Color(0xFFCFEBD9);
  static const border = Color(0xFFE6DED3);
}

class AppRadius {
  const AppRadius._();

  static const card = 20.0;
  static const pill = 999.0;
}

class AppTheme {
  const AppTheme._();

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppColors.terracotta,
      primary: AppColors.espresso,
      secondary: AppColors.terracotta,
      surface: AppColors.background,
    );
    final textTheme = GoogleFonts.plusJakartaSansTextTheme().apply(
      bodyColor: AppColors.textPrimary,
      displayColor: AppColors.textPrimary,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.background,
      textTheme: textTheme,
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        elevation: 0,
        scrolledUnderElevation: 0,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.espresso,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(52),
          shape: const StadiumBorder(),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.background,
        indicatorColor: Colors.transparent,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: states.contains(WidgetState.selected)
                ? AppColors.terracotta
                : AppColors.textMuted,
          ),
        ),
      ),
    );
  }
}
