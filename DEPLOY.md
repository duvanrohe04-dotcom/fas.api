# Despliegue en Coolify

Son dos aplicaciones del mismo repositorio: el **backend** (ya desplegado) y el
**frontend** (nuevo).

## 1. Backend (actualizar el que ya tienes)

Solo hay que volver a desplegar. Al arrancar, `init_db` añade solo las columnas
nuevas de los pedidos (tipo, nombre, notas, código de seguimiento) a tu base
existente; no se pierden datos.

Variables de entorno (Coolify → Environment Variables):

| Variable | Valor |
|---|---|
| `SECRET_KEY` | clave larga y aleatoria (obligatoria) |
| `CORS_ORIGINS` | dominio del frontend, ej. `https://cafe.midominio.com` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | solo se usan si no hay usuarios |

> Si dejas `CORS_ORIGINS` vacío o en `*`, cualquier web puede llamar a la API.
> En producción pon el dominio exacto del frontend (sin barra final).

## 2. Frontend (aplicación nueva)

1. Coolify → *New Resource* → mismo repositorio.
2. **Build Pack**: `Dockerfile`.
3. **Base Directory**: `/frontend` · **Dockerfile Location**: `/Dockerfile`.
4. **Ports Exposes**: `80`.
5. **Build Arguments** (Environment Variables marcadas como *Build Variable*):

   | Variable | Valor |
   |---|---|
   | `API_BASE_URL` | `https://api.midominio.com/api/v1` (URL pública del backend + `/api/v1`) |

6. Asigna el dominio (ej. `cafe.midominio.com`) y despliega.

`API_BASE_URL` se incrusta al compilar: si cambias la URL del backend hay que
volver a desplegar el frontend.

El primer build descarga el SDK de Flutter (~1,5 GB) y tarda varios minutos;
los siguientes reutilizan la caché de capas.

## 3. Comprobar

- `https://api.midominio.com/health` → `{"status":"ok", ...}`
- `https://cafe.midominio.com/` → tienda del cliente
- `https://cafe.midominio.com/admin` → panel interno (entra con el admin)

## Antes de abrirlo al público

- El pedido sin sesión (`POST /orders/public`) no tiene límite de intentos.
  Conviene ponerlo detrás de un limitador (por ejemplo en el proxy de Coolify).
- Las fotos de los productos son enlaces; usa imágenes alojadas por ti.
- Los datos viven en el volumen `cafeteria_data` (SQLite). Para más volumen o
  varias réplicas, cambia `DATABASE_URL` a PostgreSQL.

## CI (GitHub Actions)

`.github/workflows/tests.yml` corre en cada push/PR: ruff, black, pytest por
archivo, cobertura (mínimo 85 %), build de la imagen Docker del backend con
comprobación de `/health`, y el frontend (`flutter analyze`, `flutter test` y
`flutter build web`).
