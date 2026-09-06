"""
retriever.py - FAISS Vector Indexing & Semantic Search

Implements local FAISS vector indexing with:
- Exact cosine similarity search via IndexFlatIP with L2 normalized vectors
- Local persistence (index.faiss & metadata.pkl)
- Metadata preservation (filename, page, section, chunk_id)
- Top-K and similarity score threshold filtering
"""

import os
import pickle
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from src.chunking import Chunk
from src.embeddings import EmbeddingManager


@dataclass
class SearchResult:
    """Represents a retrieved document chunk with similarity score and metadata."""
    chunk_id: str
    text: str
    score: float  # Cosine similarity score (higher is more similar, range [-1, 1], typically [0, 1])
    metadata: Dict[str, Any]

    @property
    def filename(self) -> str:
        return str(self.metadata.get("filename", "Unknown"))

    @property
    def page_number(self) -> int:
        return int(self.metadata.get("page_number", 1))

    @property
    def section(self) -> str:
        return str(self.metadata.get("section", "General"))


class FAISSRetriever:
    """
    Local vector store backed by FAISS IndexFlatIP (Cosine Similarity).
    Maintains parallel metadata store and handles index persistence.
    """

    def __init__(self, embedding_manager: EmbeddingManager, index_dir: str = "vectorstore"):
        self.embedding_manager = embedding_manager
        self.index_dir = index_dir
        self.index: Optional[Any] = None
        self.chunks_data: List[Dict[str, Any]] = []  # Parallel list of chunk texts & metadata

        os.makedirs(self.index_dir, exist_ok=True)

    @property
    def total_vectors(self) -> int:
        return self.index.ntotal if self.index is not None else 0

    def is_indexed(self) -> bool:
        """Checks if a valid index is currently loaded in memory or on disk."""
        if self.index is not None and self.total_vectors > 0:
            return True
        index_file = os.path.join(self.index_dir, "index.faiss")
        meta_file = os.path.join(self.index_dir, "metadata.pkl")
        return os.path.isfile(index_file) and os.path.isfile(meta_file)

    def build_index(self, chunks: List[Chunk], force_rebuild: bool = False) -> int:
        """
        Builds a new FAISS index from a list of Chunks.
        Overwrites existing index if force_rebuild=True.
        """
        if faiss is None:
            raise ImportError("faiss-cpu is required. Please install faiss-cpu.")

        if not chunks:
            return 0

        # Extract texts for embedding
        texts = [c.text for c in chunks]
        embeddings = self.embedding_manager.embed_texts(texts, normalize=True)

        dim = embeddings.shape[1]
        # Using IndexFlatIP for cosine similarity on unit-normalized vectors
        new_index = faiss.IndexFlatIP(dim)
        new_index.add(embeddings)

        self.index = new_index
        self.chunks_data = [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "metadata": c.metadata,
            }
            for c in chunks
        ]

        # Automatically save index and metadata to disk
        self.save()
        return self.total_vectors

    def add_chunks(self, chunks: List[Chunk]) -> int:
        """Adds additional chunks to an existing index."""
        if not chunks:
            return self.total_vectors

        if self.index is None:
            return self.build_index(chunks)

        texts = [c.text for c in chunks]
        embeddings = self.embedding_manager.embed_texts(texts, normalize=True)
        self.index.add(embeddings)

        for c in chunks:
            self.chunks_data.append({
                "chunk_id": c.chunk_id,
                "text": c.text,
                "metadata": c.metadata,
            })

        self.save()
        return self.total_vectors

    def save(self, directory: Optional[str] = None) -> None:
        """Persists the FAISS index and metadata store to disk."""
        if faiss is None:
            raise ImportError("faiss-cpu is required to save vector index.")

        target_dir = directory or self.index_dir
        os.makedirs(target_dir, exist_ok=True)

        if self.index is not None:
            index_path = os.path.join(target_dir, "index.faiss")
            faiss.write_index(self.index, index_path)

        meta_path = os.path.join(target_dir, "metadata.pkl")
        with open(meta_path, "wb") as f:
            pickle.dump(self.chunks_data, f)

    def load(self, directory: Optional[str] = None) -> bool:
        """Loads index and metadata from disk if available."""
        if faiss is None:
            return False

        target_dir = directory or self.index_dir
        index_path = os.path.join(target_dir, "index.faiss")
        meta_path = os.path.join(target_dir, "metadata.pkl")

        if not (os.path.isfile(index_path) and os.path.isfile(meta_path)):
            return False

        try:
            self.index = faiss.read_index(index_path)
            with open(meta_path, "rb") as f:
                self.chunks_data = pickle.load(f)
            return True
        except Exception as e:
            print(f"Warning: Failed to load FAISS index: {e}")
            return False

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Retrieves top_k most similar chunks for a given query string.
        Filters by similarity_threshold if provided (e.g. 0.35).
        """
        if self.index is None or self.total_vectors == 0:
            # Attempt loading from disk
            loaded = self.load()
            if not loaded:
                return []

        # Embed query with the same model
        query_vec = self.embedding_manager.embed_query(query, normalize=True)
        query_vec_2d = np.expand_dims(query_vec, axis=0)

        # Retrieve top_k candidates
        effective_k = min(top_k, self.total_vectors)
        distances, indices = self.index.search(query_vec_2d, effective_k)

        results: List[SearchResult] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks_data):
                continue

            float_score = float(score)

            # Apply similarity threshold if set
            if similarity_threshold is not None and float_score < similarity_threshold:
                continue

            chunk_info = self.chunks_data[idx]
            result = SearchResult(
                chunk_id=chunk_info["chunk_id"],
                text=chunk_info["text"],
                score=round(float_score, 4),
                metadata=chunk_info["metadata"],
            )
            results.append(result)

        return results
