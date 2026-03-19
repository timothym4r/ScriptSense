import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "ScriptSense Backend"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./scriptsense.db",
    )


settings = Settings()
