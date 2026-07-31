"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file or environment variables."""

    # App
    APP_NAME: str = "CodeMentor"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite:///./codementor.db"

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Groq AI (sole AI provider)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Backward-compatible alias used by older env files
    GROQ_DEFAULT_MODEL: str = ""

    # Compiler
    COMPILER_PROVIDER: str = "local"
    PISTON_API_URL: str = "https://emkc.org/api/v2/piston"

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000"

    # Rate limiting
    CHAT_RATE_LIMIT_PER_MINUTE: int = 30

    @property
    def groq_model(self) -> str:
        """Resolved default Groq model (GROQ_MODEL preferred)."""
        return (self.GROQ_MODEL or self.GROQ_DEFAULT_MODEL or "llama-3.3-70b-versatile").strip()

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


# Global settings instance
settings = Settings()
