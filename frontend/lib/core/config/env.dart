/// Configuración de entorno. Se sobrescribe al compilar:
/// `flutter run -d chrome --dart-define=API_BASE_URL=https://mi-api/api/v1`
class Env {
  const Env._();

  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8010/api/v1',
  );
}
