"""Phase 0: central settings loaded from .env (pydantic-settings)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API keys
    openai_api_key: str = ""
    pinecone_api_key: str = ""
    tavily_api_key: str = ""

    # Provider: "ollama" (local, free) or "openai"
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"

    # Models (names depend on the provider)
    llm_model: str = "qwen2.5:7b"          # final answer generation
    grader_model: str = "qwen2.5:7b"       # structured yes/no graders
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768               # nomic-embed-text=768, text-embedding-3-small=1536

    # Pinecone (index dimension must equal embedding_dim)
    pinecone_index: str = "incident-kb-768"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # Self-RAG loop limits
    retrieval_k: int = 4
    relevance_min_docs: int = 1
    max_rewrites: int = 2
    max_generations: int = 3
    web_results: int = 3

    # Storage
    checkpoint_db: str = "data/sqlite/checkpoints.db"
    app_db: str = "data/sqlite/app.db"

    # Upload limits
    max_upload_mb: int = 10
    allowed_extensions: str = ".pdf,.md,.txt,.docx"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
