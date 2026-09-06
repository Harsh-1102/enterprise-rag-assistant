"""
embeddings.py - Dense Vector Embedding Pipeline

Uses Sentence-Transformers to generate normalized 384-dimensional dense
embeddings. Guarantees identical embedding model for both document indexing
and query retrieval.
"""

from typing import List, Optional
import numpy as np


class EmbeddingManager:
    """
    Manages embedding model lifecycle, batch inference, and normalization.
    Uses 'all-MiniLM-L6-v2' by default (fast, high-accuracy, 384 dimensions).
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._embedding_dim = 384

    @property
    def model(self):
        """Lazy-loads the SentenceTransformer model on first invocation."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(
                    self.model_name, device=self.device
                )
                self._embedding_dim = (
                    self._model.get_sentence_embedding_dimension()
                )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load embedding model '{self.model_name}'. "
                    f"Ensure 'sentence-transformers' is installed. "
                    f"Error: {str(e)}"
                ) from e
        return self._model

    @property
    def embedding_dim(self) -> int:
        """Returns the embedding vector dimensionality."""
        return self._embedding_dim

    def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Embeds a list of text strings into a 2D numpy array of shape (N, D).
        When normalize=True, vectors are unit-normalized (L2 norm = 1.0),
        allowing inner product search to equal cosine similarity.
        """
        if not texts:
            return np.empty((0, self.embedding_dim), dtype=np.float32)

        raw_embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return raw_embeddings.astype(np.float32)

    def embed_query(self, query: str, normalize: bool = True) -> np.ndarray:
        """
        Embeds a single query string into a 1D numpy array of shape (D,).
        Uses the exact same embedding model as document chunks.
        """
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Query string cannot be empty.")

        embedding = self.model.encode(
            clean_query,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )
        return embedding.astype(np.float32)
