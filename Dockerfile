FROM python:3.13-slim

# Evitar que Python escriba archivos .pyc y forzar salida estándar (útil en Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema necesarias para PostgreSQL (psycopg2/asyncpg si se requiere luego)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . .

# Exponer el puerto
EXPOSE 8000

# Inicializa el esquema y el administrador antes de arrancar.
# `exec` deja uvicorn como PID 1 para que reciba las señales de parada.
CMD ["sh", "-c", "python -m app.scripts.init_db && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
