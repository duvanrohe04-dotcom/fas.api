/// Configuración de entorno. Se sobrescribe al compilar:
/// `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1`
/// (10.0.2.2 es el "localhost" del PC visto desde el emulador de Android).
///
/// Por defecto apunta al backend de producción, que es lo que necesita el APK.
class Env {
  const Env._();

  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://fastapi.sbs.mom/api/v1',
  );
}
