"""Application configuration.

All configuration is environment-driven. See ``.env.example`` for the full
list. Sensible zero-config defaults are chosen so that Demo Mode runs with no
external services (SQLite database, in-memory vector store, deterministic demo
LLM generator).
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- App ----
    app_name: str = "RePersona"
    env: str = Field(default="development")
    debug: bool = Field(default=True)

    # When true, the backend never reaches out to the network. Persona builds
    # use the bundled, clearly-labelled demonstration corpus and a deterministic
    # local generator. This is the default so the project runs out of the box.
    demo_mode: bool = Field(default=True)

    # ---- Database ----
    # Defaults to a local SQLite file so no PostgreSQL server is required for a
    # demo. Point DATABASE_URL at PostgreSQL in production, e.g.
    # postgresql+psycopg2://user:pass@host:5432/repersona
    database_url: str = Field(default="sqlite:///./repersona.db")

    # ---- CORS ----
    # Comma-separated string (kept as a plain str so pydantic-settings does not
    # try to JSON-decode it from the .env file). Use `cors_origins_list` to read
    # the parsed list.
    cors_origins: str = Field(default="http://localhost:3000")

    # ---- Source discovery mode ----
    # "auto"/"wikipedia": collect real data live from Wikipedia/Wikiquote/Wikimedia.
    # "demo": only use the bundled synthetic corpus (offline).
    source_mode: str = Field(default="auto")
    wikipedia_lang: str = Field(default="en")

    # ---- LLM (Llama) ----
    # provider: "auto" | "demo" | "ollama" | "openai_compatible"
    # "auto" uses Ollama if it's reachable, otherwise the offline demo composer.
    llm_provider: str = Field(default="auto")
    llm_base_url: str = Field(default="http://127.0.0.1:11434")
    llm_model: str = Field(default="llama3.2:3b")
    llm_api_key: str = Field(default="")
    llm_temperature: float = Field(default=0.4)
    llm_max_tokens: int = Field(default=768)
    llm_timeout_seconds: float = Field(default=60.0)

    # ---- Embeddings ----
    # When sentence-transformers is unavailable the embedding service falls back
    # to a deterministic hashing/TF-IDF vectoriser (see services/embeddings.py).
    embedding_model: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")
    embedding_dim: int = Field(default=384)

    # ---- Vector store ----
    # provider: "faiss" | "memory". Falls back to "memory" if faiss is missing.
    vector_db: str = Field(default="faiss")
    vector_dir: str = Field(default="./data/vector")

    # ---- Whisper (speech-to-text) ----
    whisper_model: str = Field(default="base")
    whisper_device: str = Field(default="cpu")

    # ---- Storage ----
    storage_backend: str = Field(default="local")  # local | s3
    storage_dir: str = Field(default="./data/storage")
    s3_bucket: str = Field(default="")
    s3_endpoint_url: str = Field(default="")

    # ---- Workers / queue (optional) ----
    redis_url: str = Field(default="")

    # ---- Source discovery (optional external search) ----
    # search_provider: "" (disabled) | "tavily" | "serpapi"
    search_api_key: str = Field(default="")
    search_provider: str = Field(default="")

    # ---- YouTube (optional video/interview discovery) ----
    youtube_api_key: str = Field(default="")

    # ---- News (optional) ----
    news_api_key: str = Field(default="")

    # ---- Limits / security ----
    max_question_chars: int = Field(default=2000)
    rate_limit_per_minute: int = Field(default=60)

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
