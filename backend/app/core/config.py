from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "企业安全运营平台"
    app_version: str = "0.1.0"
    environment: str = "development"
    database_url: str = ""
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    rate_limit_requests: int = 300
    rate_limit_window_seconds: int = 60
    login_failure_limit: int = 5
    login_failure_window_seconds: int = 900
    redis_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"
    nvd_api_key: str = ""
    nvd_sync_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
