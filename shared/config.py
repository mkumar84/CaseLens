import os

from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        # Normalize common Supabase/Postgres URL forms to the async driver.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    # No DATABASE_URL configured: fall back to a local SQLite file so the
    # backend, gateway, seed script, and demo script are runnable without
    # a live Supabase instance.
    default_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "caselens.db")
    return f"sqlite+aiosqlite:///{default_path}"


class Settings:
    database_url: str = _database_url()
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    gateway_url: str = os.getenv("GATEWAY_URL", "http://127.0.0.1:8001")
    backend_url: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


settings = Settings()
