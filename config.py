from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys — at least one LLM key required (validated below)
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    huggingfacehub_access_token: Optional[str] = None

    # Paths
    db_path: str = "vectorDB/my_FAISS_db"
    retriever_path: str = "vectorDB/retriever.pkl"
    data_path: str = "data/"
    chat_history_path: str = "chat_history.json"

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # LLM
    openai_model: str = "gpt-4o"
    groq_model: str = "llama-3.1-8b-instant"
    temperature: float = 0.3
    max_tokens: int = 1500
    llm_timeout: int = 60

    # Retrieval
    retriever_k: int = 12
    retriever_fetch_k: int = 25
    retriever_lambda_mult: float = 0.7
    max_context_docs: int = 20

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    @model_validator(mode="after")
    def require_at_least_one_llm_key(self) -> "AppConfig":
        if not self.openai_api_key and not self.groq_api_key:
            raise ValueError(
                "At least one of OPENAI_API_KEY or GROQ_API_KEY must be set in the .env file"
            )
        return self


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    return AppConfig()
