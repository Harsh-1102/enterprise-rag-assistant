"""
chunking.py - Semantic Chunking Strategy with Metadata Preservation

Splits extracted documents into optimal overlapping chunks for dense vector embedding.
Preserves parent document metadata:
- filename, page_number, section, doc_id
- Adds chunk_id, chunk_index, token/character count.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from src.document_loader import Document


@dataclass
class Chunk:
    """Represents a text chunk ready for vector embedding and retrieval."""
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: str = ""

    def __post_init__(self):
        if not self.chunk_id:
            doc_id = self.metadata.get("doc_id", "doc")
            idx = self.metadata.get("chunk_index", 0)
            self.chunk_id = f"{doc_id}_c{idx:04d}"
            self.metadata["chunk_id"] = self.chunk_id

    @property
    def filename(self) -> str:
        return str(self.metadata.get("filename", "Unknown"))

    @property
    def page_number(self) -> int:
        return int(self.metadata.get("page_number", 1))

    @property
    def section(self) -> str:
        return str(self.metadata.get("section", "General"))


class DocumentChunker:
    """
    Configurable recursive character splitter with overlap and semantic boundary respect.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 60):
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively breaks text using natural linguistic boundaries."""
        if len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []

        if not separators:
            # Hard split if no separators left
            return [text[i : i + self.chunk_size].strip() for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        sep = separators[0]
        splits = text.split(sep)
        good_splits: List[str] = []

        current_piece = ""
        for piece in splits:
            if not piece.strip():
                continue
            candidate = f"{current_piece}{sep}{piece}" if current_piece else piece
            if len(candidate) <= self.chunk_size:
                current_piece = candidate
            else:
                if current_piece:
                    good_splits.append(current_piece.strip())
                if len(piece) > self.chunk_size:
                    # Recurse with finer separator on large piece
                    sub_pieces = self._split_text_recursive(piece, separators[1:])
                    good_splits.extend(sub_pieces)
                    current_piece = ""
                else:
                    current_piece = piece

        if current_piece.strip():
            good_splits.append(current_piece.strip())

        # Merge with sliding window overlap
        chunks: List[str] = []
        i = 0
        while i < len(good_splits):
            combined = good_splits[i]
            j = i + 1
            while j < len(good_splits) and (len(combined) + len(sep) + len(good_splits[j])) <= self.chunk_size:
                combined += f"{sep}{good_splits[j]}"
                j += 1

            chunks.append(combined.strip())
            # Advance index ensuring overlap
            if j == i + 1:
                i += 1
            else:
                i = max(i + 1, j - 1)

        return chunks

    def chunk_document(self, document: Document, start_index: int = 0) -> List[Chunk]:
        """Splits a single document into tagged Chunks inheriting metadata."""
        raw_text = document.content.strip()
        if not raw_text:
            return []

        text_pieces = self._split_text_recursive(raw_text, self.separators)
        chunks: List[Chunk] = []

        for idx, piece in enumerate(text_pieces):
            if not piece.strip():
                continue

            meta = dict(document.metadata)
            chunk_idx = start_index + idx
            meta["chunk_index"] = chunk_idx
            meta["char_length"] = len(piece)
            meta["word_count"] = len(piece.split())

            chunk = Chunk(text=piece, metadata=meta)
            chunks.append(chunk)

        return chunks

    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """Batch chunks a list of Document objects preserving global chunk index."""
        all_chunks: List[Chunk] = []
        global_idx = 0
        for doc in documents:
            doc_chunks = self.chunk_document(doc, start_index=global_idx)
            all_chunks.extend(doc_chunks)
            global_idx += len(doc_chunks)
        return all_chunks
