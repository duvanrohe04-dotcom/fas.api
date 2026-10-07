import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Se inicializa en `main()` con la instancia real.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('sharedPreferencesProvider no inicializado'),
);

final tokenStoreProvider = Provider<TokenStore>(
  (ref) => TokenStore(ref.watch(sharedPreferencesProvider)),
);

/// Persiste el JWT entre recargas de la web.
class TokenStore {
  TokenStore(this._prefs);

  static const _key = 'access_token';
  final SharedPreferences _prefs;

  String? read() => _prefs.getString(_key);
  Future<void> save(String token) => _prefs.setString(_key, token);
  Future<void> clear() => _prefs.remove(_key);
}
