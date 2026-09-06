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
]
