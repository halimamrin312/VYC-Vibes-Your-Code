"""
swarm/config.py
Pydantic Settings configurations for loading and validating environment variables.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    model_provider: str = Field(default="gemini", validation_alias="MODEL_PROVIDER")
    model_name: str = Field(default="gemini-2.5-flash", validation_alias="MODEL_NAME")
    
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8000, validation_alias="PORT")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    data_room_dir: str = Field(default="data_room", validation_alias="DATA_ROOM_DIR")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

settings = Settings()
