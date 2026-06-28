"""
Xythe Cloud - Configuration
All settings loaded from environment variables.
"""
from dotenv import load_dotenv
load_dotenv()

import os
from functools import lru_cache


class Settings:
    """Application settings."""
    
    # App
    APP_NAME: str = "Xythe Cloud"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://xythe:xythe_secret@localhost:5432/xythe_cloud"
    )
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # ChromaDB
    CHROMA_PERSIST_DIR: str = os.getenv(
        "CHROMA_PERSIST_DIR",
        "./data/chromadb"
    )
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small"
    )
    
    # WhatsApp
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv(
        "WHATSAPP_VERIFY_TOKEN",
        "xythe_whatsapp_verify_2026"
    )
    WHATSAPP_API_VERSION: str = "v21.0"
    
    # Security
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    
    # Rate Limiting
    API_RATE_LIMIT: int = int(os.getenv("API_RATE_LIMIT", "100"))
    
    # Storage
    S3_BUCKET: str = os.getenv("S3_BUCKET", "xythe-cloud-storage")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()