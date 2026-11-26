"""Phase 0-2: chat + embedding factories. LLM_PROVIDER picks Ollama (local) or OpenAI."""
from functools import lru_cache

from app.config import get_settings


def llm_service_name() -> str:
    return "Ollama" if get_settings().llm_provider == "ollama" else "OpenAI"


def _chat(model: str, timeout: int):
    s = get_settings()
    if s.llm_provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model, temperature=0, base_url=s.ollama_base_url,
                          client_kwargs={"timeout": timeout})
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model, temperature=0, api_key=s.openai_api_key,
                      timeout=timeout, max_retries=1)


@lru_cache
def get_llm():
    return _chat(get_settings().llm_model, timeout=180)


@lru_cache
def get_grader_llm():
    return _chat(get_settings().grader_model, timeout=120)


@lru_cache
def get_embeddings():
    s = get_settings()
    if s.llm_provider == "ollama":
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model=s.embedding_model, base_url=s.ollama_base_url)
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=s.embedding_model, api_key=s.openai_api_key)
