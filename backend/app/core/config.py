import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "ScriptSense Backend"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./scriptsense.db",
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
        if origin.strip()
    )


settings = Settings()
