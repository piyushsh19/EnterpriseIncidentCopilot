"""Phase 1: split text into overlapping chunks with metadata."""
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk(text: str, base_metadata: dict, size: int = 3200, overlap: int = 400) -> List[Document]:
    """~800 tokens per chunk (about 4 chars/token) with ~100 tokens overlap."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return [
        Document(page_content=piece, metadata={**base_metadata, "chunk_index": i})
        for i, piece in enumerate(splitter.split_text(text))
    ]
