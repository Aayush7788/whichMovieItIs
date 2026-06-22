from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
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

    frontend_origins: str = "http://localhost:5173"

    def get_frontend_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]

    def build_database_url(self) -> str:
        if self.database_url:
            return str(self.database_url)
        return(
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
settings = Settings()   
