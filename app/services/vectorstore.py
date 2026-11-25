"""Phase 0-2: Pinecone index + LangChain vector store / retriever."""
from functools import lru_cache
from typing import Optional

from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from app.config import get_settings
from app.services.llm import get_embeddings


@lru_cache
def get_pinecone() -> Pinecone:
    return Pinecone(api_key=get_settings().pinecone_api_key)


def ensure_index() -> None:
    """Create the serverless index once (dimension must match the embedding model)."""
    s = get_settings()
    pc = get_pinecone()
    if s.pinecone_index not in pc.list_indexes().names():
        pc.create_index(
            name=s.pinecone_index,
            dimension=s.embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud=s.pinecone_cloud, region=s.pinecone_region),
        )


@lru_cache
def get_vectorstore() -> PineconeVectorStore:
    s = get_settings()
    return PineconeVectorStore(index=get_pinecone().Index(s.pinecone_index),
                               embedding=get_embeddings())


def get_retriever(service: Optional[str] = None):
    """k nearest chunks, optionally filtered by service metadata."""
    kwargs = {"k": get_settings().retrieval_k}
    if service:
        kwargs["filter"] = {"service": service}
    return get_vectorstore().as_retriever(search_kwargs=kwargs)
