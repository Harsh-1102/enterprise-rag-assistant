"""
Enterprise Document Intelligence & RAG Assistant
Core package initialization.
"""

from src.document_loader import Document, DocumentLoader
from src.chunking import Chunk, DocumentChunker
from src.embeddings import EmbeddingManager
from src.retriever import FAISSRetriever, SearchResult
from src.rag_pipeline import RAGPipeline
from src.evaluation import RAGEvaluator
from src.source_viewer import (
    resolve_source,
    render_source_cards,
    render_pdf_viewer,
    render_docx_preview,
    save_uploaded_document,
)

__all__ = [
    "Document",
    "DocumentLoader",
    "Chunk",
    "DocumentChunker",
    "EmbeddingManager",
    "FAISSRetriever",
    "SearchResult",
    "RAGPipeline",
    "RAGEvaluator",
    "resolve_source",
    "render_source_cards",
    "render_pdf_viewer",
    "render_docx_preview",
    "save_uploaded_document",
]
