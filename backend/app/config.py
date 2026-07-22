from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: PostgresDsn | None=None

    db_host: str = "localhost"
    db_port: int = 15432
    db_name: str = "whichmovie"
    db_user: str = "postgres"
    db_password: str = "whichmovie123!"
    tmdb_read_access_token: str | None = None
    tmdb_api_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p"
    tmdb_poster_size: str = "w342"
    tmdb_timeout_seconds: float = 10.0
    tmdb_runtime_fallback_timeout_seconds: float = 3.0
    tmdb_runtime_fallback_max_attempts: int = 1
    tmdb_runtime_fallback_rate_limit_window_seconds: int = 60
    tmdb_runtime_fallback_max_requests_per_window: int = 10
    tmdb_runtime_fallback_query_cache_seconds: int = 1800
    tmdb_runtime_persistence_max_database_mb: int = 450
    tmdb_runtime_minimum_overview_length: int = 80
    preload_embedding_model_on_startup: bool = True
    public_api_rate_limit_enabled: bool = True
    public_api_rate_limit_window_seconds: int = 60
    public_api_search_max_requests_per_window: int = 30
    public_api_catalog_max_requests_per_window: int = 120
    log_level: str = "INFO"

    frontend_origins: str = "http://localhost:5173"

    def is_production(self) -> bool:
        return self.app_env.casefold() == "production"

    def get_frontend_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]

    def validate_production_settings(self) -> None:
        if not self.is_production():
            return

        errors = []
        frontend_origins = self.get_frontend_origins()

        if self.database_url is None:
            errors.append("DATABASE_URL is required")

        if not self.tmdb_read_access_token:
            errors.append("TMDB_READ_ACCESS_TOKEN is required")

        if self.tmdb_runtime_persistence_max_database_mb < 1:
            errors.append(
                "TMDB_RUNTIME_PERSISTENCE_MAX_DATABASE_MB must be positive"
            )

        if self.tmdb_runtime_minimum_overview_length < 1:
            errors.append(
                "TMDB_RUNTIME_MINIMUM_OVERVIEW_LENGTH must be positive"
            )

        rate_limit_values = {
            "PUBLIC_API_RATE_LIMIT_WINDOW_SECONDS": (
                self.public_api_rate_limit_window_seconds
            ),
            "PUBLIC_API_SEARCH_MAX_REQUESTS_PER_WINDOW": (
                self.public_api_search_max_requests_per_window
            ),
            "PUBLIC_API_CATALOG_MAX_REQUESTS_PER_WINDOW": (
                self.public_api_catalog_max_requests_per_window
            ),
        }

        if self.public_api_rate_limit_enabled:
            for name, value in rate_limit_values.items():
                if value < 1:
                    errors.append(f"{name} must be positive")

        if not frontend_origins:
            errors.append("FRONTEND_ORIGINS must contain at least one origin")

        if "*" in frontend_origins:
            errors.append("FRONTEND_ORIGINS cannot include '*' in production")

        localhost_origins = [
            origin
            for origin in frontend_origins
            if "localhost" in origin or "127.0.0.1" in origin
        ]

        if localhost_origins:
            errors.append(
                "FRONTEND_ORIGINS cannot use localhost in production"
            )

        if errors:
            raise ValueError(
                "invalid production settings: "
                + "; ".join(errors)
            )

    def build_database_url(self) -> str:
        if self.database_url:
            return str(self.database_url)
        return(
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
settings = Settings()   
