"""Application settings, validated once at startup."""

import secrets
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SALT_BYTES = 32


class Settings(BaseSettings):
    """Environment-driven configuration (tech.md §9.2)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", frozen=True)

    app_env: Literal["dev", "prod"] = "dev"
    app_host: str = "0.0.0.0"  # noqa: S104 - bind address inside the container
    app_port: int = Field(8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ip_hash_salt: str = ""
    face_model_path: Path = Path("models/face_detection_yunet_2023mar.onnx")
    face_score_threshold: float = Field(0.8, gt=0.0, le=1.0)
    max_photo_bytes: int = Field(10 * 1024 * 1024, gt=0)
    rate_analyze_per_hour: int = Field(20, gt=0)
    rate_papercraft_per_hour: int = Field(60, gt=0)
    cors_dev_origin: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _check_salt(self) -> Self:
        if self.app_env == "prod" and len(self.ip_hash_salt.encode()) < MIN_SALT_BYTES:
            raise ValueError(f"IP_HASH_SALT must be at least {MIN_SALT_BYTES} bytes in prod")
        return self

    @property
    def is_prod(self) -> bool:
        """Production mode flag."""
        return self.app_env == "prod"

    def salt_bytes(self) -> bytes:
        """Configured salt, or a per-process random one in dev."""
        return self.ip_hash_salt.encode() or secrets.token_bytes(MIN_SALT_BYTES)
