from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://labchain:labchain@localhost:5432/labchain"
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = Field(default=30, ge=1, le=120)
    cors_origins: list[str] = ["http://localhost:5173"]
    upload_dir: Path = Path("uploads")
    max_upload_bytes: int = 5 * 1024 * 1024
    max_import_rows: int = 1000
    rpc_url: str = "http://localhost:8545"
    chain_id: int = 31337
    chain_confirmations: int = Field(default=1, ge=1, le=12)
    contract_address: str = ""
    relayer_private_key: str = ""
    chain_config_path: Path = Path("runtime/local.json")
    ocr_enabled: bool = False
    ocr_languages: list[str] = ["en", "vi"]
    demo_password: str = ""

    @model_validator(mode="after")
    def production_checks(self):
        if "replace-with" in self.jwt_secret:
            raise ValueError("Generate JWT_SECRET using scripts/setup_env.py")
        if self.app_env != "development" and self.demo_password:
            raise ValueError("DEMO_PASSWORD must be empty outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
