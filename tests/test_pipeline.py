"""
test_pipeline.py - Automated Unit & Integration Tests

Tests:
1. Document extraction (PDF and text)
2. Semantic chunking and metadata preservation
3. Sentence-Transformers embedding consistency (384 dimensions)
4. FAISS indexing and cosine similarity retrieval
5. Grounding fallback and hallucination suppression
"""

import os
import pytest
import numpy as np

from src.document_loader import Document, DocumentLoader
from src.chunking import Chunk, DocumentChunker
from src.embeddings import EmbeddingManager
from src.retriever import FAISSRetriever
from src.rag_pipeline import RAGPipeline, INSUFFICIENT_INFO_RESPONSE


def test_document_loader_cleaning():
    loader = DocumentLoader()
    raw = "  Employee Policy   \n\n\n\nSection 1:  Leave. \r\n\tDetails here.  "
    cleaned = loader.clean_text(raw)
    assert "Employee Policy" in cleaned
    assert "Section 1: Leave." in cleaned
    assert "\r" not in cleaned
    assert "\t" not in cleaned


def test_chunking_metadata_preservation():
    chunker = DocumentChunker(chunk_size=150, chunk_overlap=30)
    sample_text = (
        "Apex Enterprise Technologies enforces strict attendance. "
        "Employees must check in by 9:15 AM each morning. "
        "Late arrivals without notification will trigger counseling after 3 incidents. "
        "Continuous unauthorized absence constitutes job abandonment."
    )
    doc = Document(
        content=sample_text,
        metadata={"filename": "Test_Attendance.pdf", "page_number": 2, "section": "Attendance"}
    )
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    for c in chunks:
        assert c.metadata["filename"] == "Test_Attendance.pdf"
        assert c.metadata["page_number"] == 2
        assert c.metadata["section"] == "Attendance"
        assert "chunk_id" in c.metadata
        assert len(c.text) <= 150 + 40  # Reasonable boundary margin


def test_embedding_manager_dimensions():
    manager = EmbeddingManager(model_name="all-MiniLM-L6-v2")
    texts = ["Annual leave is 20 days.", "Work from home is allowed 3 days per week."]
    vectors = manager.embed_texts(texts, normalize=True)

    assert vectors.shape == (2, 384)
    # Check unit norm (length == 1.0)
    norms = np.linalg.norm(vectors, axis=1)
    for norm in norms:
        assert pytest.approx(norm, rel=1e-3) == 1.0

    query_vec = manager.embed_query("How many vacation days?", normalize=True)
    assert query_vec.shape == (384,)
    assert pytest.approx(np.linalg.norm(query_vec), rel=1e-3) == 1.0


def test_faiss_retriever_index_and_search(tmp_path):
    manager = EmbeddingManager(model_name="all-MiniLM-L6-v2")
    retriever = FAISSRetriever(manager, index_dir=str(tmp_path))

    chunks = [
        Chunk(
            text="Employees get 20 days of paid annual vacation leave per calendar year.",
            metadata={"filename": "leave.pdf", "page_number": 1, "section": "Vacation"}
        ),
        Chunk(
            text="The standard resignation notice period is 30 calendar days.",
            metadata={"filename": "handbook.pdf", "page_number": 3, "section": "Resignation"}
        ),
    ]

    total = retriever.build_index(chunks, force_rebuild=True)
    assert total == 2
    assert retriever.is_indexed()

    # Search for leave query
    results = retriever.retrieve("annual vacation days", top_k=2)
    assert len(results) >= 1
    assert "20 days" in results[0].text
    assert results[0].filename == "leave.pdf"
    assert results[0].page_number == 1
    assert results[0].score > 0.40


def test_hallucination_handling_fallback(tmp_path):
    manager = EmbeddingManager(model_name="all-MiniLM-L6-v2")
    pipeline = RAGPipeline(
        index_dir=str(tmp_path),
        embedding_model_name="all-MiniLM-L6-v2",
        similarity_threshold=0.60  # Strict threshold
    )

    # Ingest only HR document
    doc = Document(
        content="Employees are provided 20 days of annual leave.",
        metadata={"filename": "Leave.pdf", "page_number": 1}
    )
    pipeline.ingest_documents([doc])

    # Out-of-domain question that should fail threshold
    response = pipeline.query("What is the distance between Mars and Jupiter?")
    assert INSUFFICIENT_INFO_RESPONSE in response.answer
    assert response.is_grounded is False
