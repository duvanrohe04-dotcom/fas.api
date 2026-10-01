# Backend Cafetería

API RESTful para la gestión de una cafetería, construida con FastAPI.

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

4. Ejecutar la aplicación en modo desarrollo:
```bash
uvicorn app.main:app --reload
```
