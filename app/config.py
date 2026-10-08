from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'CloudOps Platform'
    app_version: str = '1.0.0'
    environment: str = 'development'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()
