from pydantic import PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # APP SETTINGS
    app_name: str = "ATS Resume Intelligence"
    env: str = "development"
    port: int = 3000

    # DATABASE SETTINGS
    database_url: str

    # SECURITY SETTINGS
    jwt_secret_key: str = "super_secret_development_key_change_me_in_production"
    jwt_algorithm: str = "HS256"
    jwt_expires_in_minutes: int = 60

    # AI SETTINGS
    qdrant_url: str = "http://localhost:6333"
    qdrant_vector_size: int = 1024
    embedding_dimensions: int = 1024
    groq_api_key: str | None = None
    embedding_model_name: str = "BAAI/bge-large-en-v1.5"
    groq_chat_model: str = "llama-3.3-70b-versatile"
    similarity_threshold: float = 0.5
    top_k_chunks: int = 3

    # LLM FALLBACK & ENDPOINT SETTINGS
    llm_fallback_models: str = "openai/gpt-oss-120b,qwen/qwen3.6-27b,llama-3.3-70b-versatile"
    llm_base_url: str | None = None

    # REDIS SETTINGS
    redis_host: str = "localhost"
    redis_port: int = 6379

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
