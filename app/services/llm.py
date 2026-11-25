"""Phase 0-2: OpenAI chat + embedding factories."""
from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.llm_model, temperature=0, api_key=s.openai_api_key,
                      timeout=60, max_retries=1)


@lru_cache
def get_grader_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(model=s.grader_model, temperature=0, api_key=s.openai_api_key,
                      timeout=30, max_retries=1)


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    s = get_settings()
    return OpenAIEmbeddings(model=s.embedding_model, api_key=s.openai_api_key)
