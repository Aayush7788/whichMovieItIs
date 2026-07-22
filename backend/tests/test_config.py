import pytest

from backend.app.config import Settings


def build_settings(**overrides):
    defaults = {
        "app_env": "development",
        "database_url": None,
        "tmdb_read_access_token": None,
        "frontend_origins": "http://localhost:5173",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


def test_frontend_origins_are_trimmed():
    settings = build_settings(
        frontend_origins=(
            "https://app.vercel.app, "
            "https://admin.example.com"
        ),
    )

    assert settings.get_frontend_origins() == [
        "https://app.vercel.app",
        "https://admin.example.com",
    ]


def test_production_validation_requires_core_env():
    settings = build_settings(app_env="production")

    with pytest.raises(ValueError) as error:
        settings.validate_production_settings()

    message = str(error.value)

    assert "DATABASE_URL is required" in message
    assert "TMDB_READ_ACCESS_TOKEN is required" in message
    assert "localhost" in message


def test_production_validation_rejects_wildcard_origin():
    settings = build_settings(
        app_env="production",
        database_url=(
            "postgresql://postgres:password@example.com:5432/"
            "whichmovie"
        ),
        tmdb_read_access_token="token",
        frontend_origins="*",
    )

    with pytest.raises(ValueError, match="cannot include"):
        settings.validate_production_settings()


def test_production_validation_accepts_external_config():
    settings = build_settings(
        app_env="production",
        database_url=(
            "postgresql://postgres:password@example.com:5432/"
            "whichmovie"
        ),
        tmdb_read_access_token="token",
        frontend_origins="https://whichmovie.vercel.app",
    )

    settings.validate_production_settings()

def test_production_validation_rejects_invalid_storage_budget():
    settings = build_settings(
        app_env="production",
        database_url=(
            "postgresql://postgres:password@example.com:5432/"
            "whichmovie"
        ),
        tmdb_read_access_token="token",
        frontend_origins="https://whichmovie.vercel.app",
        tmdb_runtime_persistence_max_database_mb=0,
    )

    with pytest.raises(ValueError, match="must be positive"):
        settings.validate_production_settings()


def test_production_validation_rejects_invalid_api_rate_limit():
    settings = build_settings(
        app_env="production",
        database_url=(
            "postgresql://postgres:password@example.com:5432/"
            "whichmovie"
        ),
        tmdb_read_access_token="token",
        frontend_origins="https://whichmovie.vercel.app",
        public_api_search_max_requests_per_window=0,
    )

    with pytest.raises(ValueError, match="PUBLIC_API_SEARCH"):
        settings.validate_production_settings()

def test_production_validation_rejects_weak_tmdb_overview_gate():
    settings = build_settings(
        app_env="production",
        database_url=(
            "postgresql://postgres:password@example.com:5432/"
            "whichmovie"
        ),
        tmdb_read_access_token="token",
        frontend_origins="https://whichmovie.vercel.app",
        tmdb_runtime_minimum_overview_length=0,
    )

    with pytest.raises(ValueError, match="MINIMUM_OVERVIEW"):
        settings.validate_production_settings()