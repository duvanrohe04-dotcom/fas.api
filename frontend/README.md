# Origen Café — Frontend (Flutter web)

- `/` tienda del cliente · `/admin` panel interno.
- Estructura por funcionalidades en `lib/features/` (`customer`, `admin`, `auth`,
  `cart`, `menu`, `orders`), con `lib/core` (tema, red, router) y `lib/shared`.
- Estado con Riverpod, rutas con go_router, HTTP con Dio.

## Desarrollo

```bash
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api/v1
flutter analyze && flutter test
```

## Producción

`API_BASE_URL` se define al compilar (ver `Dockerfile` y `../DEPLOY.md`).
`tool/serve_spa.js` sirve `build/web` en local con la ruta `/admin` funcionando.
