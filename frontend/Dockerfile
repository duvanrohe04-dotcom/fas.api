# ---- Etapa 1: compilar Flutter web ------------------------------------------
FROM debian:bookworm-slim AS build

ARG FLUTTER_VERSION=3.47.6
# URL pública de la API (backend ya desplegado). Se puede sobrescribir en Coolify
# con la variable de build API_BASE_URL.
ARG API_BASE_URL=https://fastapi.sbs.mom/api/v1
ENV PUB_CACHE=/root/.pub-cache

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git unzip xz-utils \
    && rm -rf /var/lib/apt/lists/*

# SDK fijado a una versión: el mismo resultado en cada despliegue.
RUN curl -fsSL "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz" \
    | tar -xJ -C /opt \
    && git config --global --add safe.directory /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
RUN flutter config --no-analytics --enable-web \
    && flutter precache --web

WORKDIR /app
# Dependencias primero, para aprovechar la caché de capas.
COPY pubspec.yaml pubspec.lock* ./
RUN flutter pub get

COPY . .
# Si la variable llega vacía se usa el valor por defecto de arriba.
RUN API_URL="${API_BASE_URL:-https://fastapi.sbs.mom/api/v1}" \
    && echo "Compilando con API_BASE_URL=${API_URL}" \
    && flutter build web --release --no-wasm-dry-run \
       --dart-define=API_BASE_URL="${API_URL}"

# ---- Etapa 2: servir con nginx ----------------------------------------------
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz || exit 1
