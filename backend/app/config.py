from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: PostgresDsn | None=None

    db_host: str = "localhost"
    db_port: int = 55433
    db_name: str = "whichmovie"
    db_user: str = "postgres"
    db_password: str = "whichmovie123!"

    def build_database_url(self) -> str:
        if self.database_url:
            return str(self.database_url)
        return(
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
settings = Settings()   
