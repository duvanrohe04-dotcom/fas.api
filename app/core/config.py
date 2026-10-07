from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cafeteria API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str

    #: Orígenes permitidos por CORS, separados por comas. `*` permite todos
    #: (útil en desarrollo; en producción indica el dominio del frontend).
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Lista de orígenes CORS ya separada y sin espacios ni barras finales."""
        origins = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",")]
        return [o for o in origins if o] or ["*"]


settings = Settings()
