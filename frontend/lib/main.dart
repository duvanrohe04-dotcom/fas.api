import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'core/storage/token_store.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // URLs limpias (/admin) en lugar de /#/admin.
  usePathUrlStrategy();
  final prefs = await SharedPreferences.getInstance();
  // Con la tipografía ya cargada, los textos se miden bien en el primer
  // fotograma (si no, chips y botones recortan su etiqueta).
  await GoogleFonts.pendingFonts([
    GoogleFonts.plusJakartaSans(),
    GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w600),
    GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w700),
    GoogleFonts.plusJakartaSans(fontWeight: FontWeight.w800),
  ]);

  runApp(
    ProviderScope(
      overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
      child: const OrigenCafeApp(),
    ),
  );
}
