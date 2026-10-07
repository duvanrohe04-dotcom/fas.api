# Backend Cafetería

API RESTful para la gestión de una cafetería, construida con FastAPI. Incluye un
frontend web en Flutter (`frontend/`).

## Instalación y Configuración Local

1. Crear y activar el entorno virtual:
```bash
python -m venv .venv
.venv\Scripts\activate  # En Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
Copiar `.env.example` a `.env` y ajustar los valores si es necesario.

4. Crear el esquema y el administrador inicial (usa `ADMIN_EMAIL` y `ADMIN_PASSWORD`):
```bash
python -m app.scripts.init_db
```

5. Ejecutar la aplicación en modo desarrollo (documentación en `/docs`):
```bash
uvicorn app.main:app --reload
```

## Frontend (Flutter web)

Requiere Flutter instalado. Desde `frontend/`:
```bash
flutter pub get
flutter build web --dart-define=API_BASE_URL=http://localhost:8000/api/v1
node tool/serve_spa.js 5000
```

- `/` — tienda del cliente: elige productos, en mesa o para llevar, y sigue su pedido.
- `/admin` — panel interno (administrador o cajero): pedidos, cobro, mesas y productos.

## Endpoints públicos (sin sesión)

- `GET /api/v1/products`, `GET /api/v1/categories`, `GET /api/v1/tables/public`
- `POST /api/v1/orders/public` — crea un pedido y devuelve un `tracking_code`
- `GET /api/v1/orders/track/{code}` — estado del pedido para el cliente

## Tests y calidad

```bash
python -m pytest app/tests --cov=app
ruff check app && black --check app
```
