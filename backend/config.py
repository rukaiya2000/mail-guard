import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration settings."""

    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # CORS Configuration
    ALLOWED_ORIGINS: list[str] = [
        origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    ]

    # LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LITELLM_BASE_URL: str = os.getenv("LITELLM_BASE_URL", "https://api.ai.it.ufl.edu")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.1-70b-instruct")
    LLM_TEMPERATURE: float = 0.3
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_MAX_RETRIES: int = 3

    # Classification Cache
    CACHE_HOURS: int = 24

    # Rate Limiting
    RATE_LIMIT_CLASSIFY: str = "10/minute"
    RATE_LIMIT_BATCH: str = "5/minute"
    RATE_LIMIT_REGISTER: str = "5/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self):
        """Validate critical configuration settings."""
        if not self.JWT_SECRET:
            raise ValueError("JWT_SECRET environment variable must be set for production")
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable must be set")


settings = Settings()
