import unicodedata

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default='CloudOps Platform', min_length=1, max_length=100)
    app_version: str = Field(default='1.0.0', min_length=1, max_length=50)
    environment: str = Field(default='development', min_length=1, max_length=50)
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @field_validator('app_name', 'app_version', 'environment', mode='before')
    @classmethod
    def normalize_display_values(cls, value: object) -> object:
        if isinstance(value, str):
            if any(unicodedata.category(character) == 'Cc' for character in value):
                raise ValueError('configuration values must not contain control characters')
            return value.strip()
        return value


settings = Settings()
