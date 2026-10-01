from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="API RESTful para la gestión de una cafetería.",
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"], summary="Verificar estado de la API")
def health_check():
    """
    Endpoint para comprobar que la aplicación está corriendo correctamente.
    """
    return {"status": "ok", "message": "API is running"}


app.include_router(api_router, prefix=settings.API_V1_STR)
