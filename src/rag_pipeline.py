"""
rag_pipeline.py - Complete Enterprise RAG Orchestrator

Integrates:
- Document Loading & Text Extraction
- Chunking & Metadata Tagging
- Dense Sentence-Transformer Embeddings
- FAISS Vector Database Indexing & Search
- Gemini Generative LLM with strict grounding prompt
- Hallucination prevention & confidence thresholding
- Conversational memory for multi-turn dialogue
- Precise source attribution
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import dotenv
from src.chunking import DocumentChunker
from src.document_loader import Document, DocumentLoader
from src.embeddings import EmbeddingManager
from src.retriever import FAISSRetriever, SearchResult

dotenv.load_dotenv()

# Predefined standard fallback string when evidence is missing
INSUFFICIENT_INFO_RESPONSE = (
    "I could not find sufficient information in the provided "
    "documents to answer this question."
)


@dataclass
class ConversationTurn:
    """Represents a single query-answer turn in conversational memory."""
    role: str  # "user" or "assistant"
    content: str
    sources: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RAGResponse:
    """Complete RAG response containing answer, sources, and context."""
    answer: str
    sources: List[Dict[str, Any]]
    retrieved_chunks: List[SearchResult]
    query: str
    is_grounded: bool
    retrieval_confidence: float
    execution_time: float


class GeminiLLMClient:
    """
    Wrapper for Google Gemini API using the official Google GenAI SDK.
    Handles authentication, prompting, error handling, and offline fallback.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.6-flash"
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = (
            model_name or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        )
        self._is_available: bool = False
        self._client: Optional[Any] = None
        self._init_client()

    def _init_client(self):
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                # Modern Google GenAI SDK (google-genai)
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                self._is_available = True
            except Exception as e:
                # Fallback to legacy google.generativeai if available
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self._client = legacy_genai.GenerativeModel(
                        model_name=self.model_name,
                        generation_config={
                            "temperature": 0.1,
                            "top_p": 0.9,
                            "max_output_tokens": 1024,
                        },
                    )
                    self._is_available = True
                except Exception as inner_e:
                    print(
                        f"Warning: Failed to init Google Gemini client: "
                        f"{e}; {inner_e}"
                    )
                    self._is_available = False
        else:
            self._is_available = False

    def is_available(self) -> bool:
        return self._is_available

    def generate(self, prompt: str) -> str:
        """Invokes the Gemini LLM with auto-model fallback and error handling."""
        if not self._is_available or self._client is None:
            context_part = ""
            if "--- RETRIEVED ENTERPRISE CONTEXT ---" in prompt:
                after_ctx = prompt.split(
                    "--- RETRIEVED ENTERPRISE CONTEXT ---"
                )[-1]
                context_part = after_ctx.split("--- QUESTION ---")[0].strip()

            return (
                "[GEMINI_API_KEY Missing / Not Configured]\n\n"
                "Based on the retrieved enterprise documents, here is the "
                "context summary:\n\n"
                f"{context_part[:600]}...\n\n"
                "*(Note: To generate full conversational answers with Google "
                "Gemini, configure your `GEMINI_API_KEY` in your local `.env` "
                "file or Streamlit Community Cloud Secrets.)*"
            )

        # Candidate models list with fallback in case of regional or account deprecation
        candidate_models = [self.model_name]
        for fallback_model in ["gemini-3.6-flash", "gemini-2.5-flash"]:
            if fallback_model not in candidate_models:
                candidate_models.append(fallback_model)

        last_error = ""
        for model_to_try in candidate_models:
            try:
                # Modern Google GenAI SDK (google-genai)
                if hasattr(self._client, "models") and hasattr(
                    self._client.models, "generate_content"
                ):
                    from google.genai import types
                    response = self._client.models.generate_content(
                        model=model_to_try,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            top_p=0.9,
                            max_output_tokens=1024,
                        ),
                    )
                    if response and response.text:
                        self.model_name = model_to_try
                        return response.text.strip()
                # Fallback legacy GenerativeModel
                elif hasattr(self._client, "generate_content"):
                    response = self._client.generate_content(prompt)
                    if response and response.text:
                        return response.text.strip()

            except Exception as e:
                last_error = str(e)
                # If 404 / model not found, loop to next candidate model
                if "404" in last_error or "NOT_FOUND" in last_error or "not found" in last_error.lower():
                    continue
                else:
                    return f"Error communicating with Gemini API: {last_error}"

        if last_error:
            return f"Error communicating with Gemini API: {last_error}"
        return INSUFFICIENT_INFO_RESPONSE


class RAGPipeline:
    """
    High-level coordinator for Enterprise Document Intelligence & RAG.
    """

    def __init__(
        self,
        index_dir: str = "vectorstore",
        embedding_model_name: str = "all-MiniLM-L6-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 60,
        gemini_api_key: Optional[str] = None,
        similarity_threshold: float = 0.35,
    ):
        self.loader = DocumentLoader()
        self.chunker = DocumentChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.embedding_manager = EmbeddingManager(
            model_name=embedding_model_name
        )
        self.retriever = FAISSRetriever(
            self.embedding_manager, index_dir=index_dir
        )
        self.llm = GeminiLLMClient(api_key=gemini_api_key)
        self.similarity_threshold = similarity_threshold
        self.conversation_history: List[ConversationTurn] = []

    def set_gemini_key(self, api_key: str):
        """Updates Gemini API key dynamically (e.g. via Streamlit UI)."""
        self.llm = GeminiLLMClient(api_key=api_key)

    def update_chunking_config(self, chunk_size: int, chunk_overlap: int):
        """Updates chunking hyperparameters."""
        self.chunker = DocumentChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def clear_memory(self):
        """Clears the conversational memory history."""
        self.conversation_history.clear()

    def ingest_documents(
        self,
        documents: List[Document],
        force_rebuild: bool = True
    ) -> Dict[str, Any]:
        """
        Full ingestion pipeline:
        1. Clean and chunk documents
        2. Generate dense embeddings
        3. Index into FAISS
        """
        chunks = self.chunker.chunk_documents(documents)
        if not chunks:
            return {"status": "empty", "num_documents": 0, "num_chunks": 0}

        num_indexed = self.retriever.build_index(
            chunks, force_rebuild=force_rebuild
        )
        return {
            "status": "success",
            "num_documents": len(documents),
            "num_chunks": len(chunks),
            "total_vectors": num_indexed,
        }

    def _build_contextual_query(self, user_query: str) -> str:
        """
        Resolves multi-turn conversational context for retrieval if pronouns
        or follow-up indicators are present.
        """
        if not self.conversation_history:
            return user_query

        # Get last turn
        last_turn = self.conversation_history[-1]
        follow_up_tokens = [
            "what about", "and for", "how about", "what if",
            "it", "they", "them", "that", "this"
        ]
        lower_q = user_query.lower()

        needs_context = (
            any(tok in lower_q for tok in follow_up_tokens)
            or len(user_query.split()) <= 4
        )
        if needs_context and last_turn.role == "user":
            return f"{last_turn.content} - {user_query}"
        return user_query

    def _build_prompt(self, query: str, chunks: List[SearchResult]) -> str:
        """
        Constructs the strict grounding prompt instructing the LLM:
        - Answer ONLY using retrieved context
        - Never hallucinate
        - Cite sources
        - If info is missing, return INSUFFICIENT_INFO_RESPONSE
        """
        context_blocks = []
        for idx, chunk in enumerate(chunks, start=1):
            fname = chunk.filename
            page = chunk.page_number
            sec = chunk.section
            block = (
                f"[Source {idx}]: File: {fname} | Page: {page} | "
                f"Section: {sec}\n{chunk.text}"
            )
            context_blocks.append(block)
        formatted_context = "\n\n".join(context_blocks)

        # Recent conversation turns (last 2 pairs)
        history_context = ""
        if len(self.conversation_history) > 0:
            turns = self.conversation_history[-4:]
            formatted_turns = [
                f"{t.role.capitalize()}: {t.content}" for t in turns
            ]
            history_context = (
                "Conversation History (for context only):\n"
                + "\n".join(formatted_turns)
                + "\n\n"
            )

        prompt = (
            "You are the official Enterprise AI Document Assistant.\n"
            "Your task is to answer employee and management questions "
            "strictly and accurately based on the provided enterprise "
            "policy documents.\n\n"
            "CRITICAL OPERATIONAL RULES:\n"
            "1. Grounding: Answer ONLY using the facts explicitly stated in "
            "the RETRIEVED ENTERPRISE CONTEXT below.\n"
            "2. Anti-Hallucination: Do NOT use any external knowledge, "
            "assumptions, or extrapolations. Do NOT invent policies.\n"
            "3. Fallback: If the exact answer cannot be determined from the "
            "provided context, or if the context is insufficient, your "
            "entire answer MUST begin with:\n"
            f'   "{INSUFFICIENT_INFO_RESPONSE}"\n'
            "   Then politely state what specific information was not found.\n"
            "4. Professionalism: Be clear, concise, structured, and formal.\n"
            "5. Source Attribution: Whenever you make a factual claim, cite "
            "the supporting document and page number in brackets, e.g. "
            "[Leave_Policy.pdf - Page 2].\n\n"
            f"{history_context}"
            "--- RETRIEVED ENTERPRISE CONTEXT ---\n"
            f"{formatted_context}\n\n"
            "--- QUESTION ---\n"
            f"{query}\n\n"
            "--- GROUNDED ANSWER ---"
        )
        return prompt

    def query(
        self,
        user_query: str,
        top_k: int = 4,
        similarity_threshold: Optional[float] = None
    ) -> RAGResponse:
        """
        Executes end-to-end RAG pipeline:
        1. Contextualize query with memory
        2. FAISS similarity retrieval
        3. Threshold confidence check
        4. LLM response generation
        5. Source extraction and memory update
        """
        start_time = time.time()
        thresh = (
            similarity_threshold
            if similarity_threshold is not None
            else self.similarity_threshold
        )

        # Step 1: Contextualize query
        contextual_query = self._build_contextual_query(user_query)

        # Step 2: Semantic retrieval from FAISS
        retrieved_chunks = self.retriever.retrieve(
            query=contextual_query,
            top_k=top_k,
            similarity_threshold=None,
        )

        # Calculate retrieval confidence (highest similarity score)
        top_score = retrieved_chunks[0].score if retrieved_chunks else 0.0

        # Step 3: Confidence & Hallucination check
        if not retrieved_chunks or top_score < thresh:
            answer = (
                f"{INSUFFICIENT_INFO_RESPONSE}\n\n"
                f"The semantic similarity score ({top_score:.2f}) was below "
                f"the confidence threshold ({thresh:.2f}). "
                f"No relevant enterprise document could be matched to: "
                f"'{user_query}'."
            )
            resp = RAGResponse(
                answer=answer,
                sources=[],
                retrieved_chunks=retrieved_chunks,
                query=user_query,
                is_grounded=False,
                retrieval_confidence=top_score,
                execution_time=round(time.time() - start_time, 3),
            )
            self.conversation_history.append(
                ConversationTurn(role="user", content=user_query)
            )
            self.conversation_history.append(
                ConversationTurn(role="assistant", content=answer, sources=[])
            )
            return resp

        # Step 4: Extract deduplicated sources
        sources: List[Dict[str, Any]] = []
        seen_sources = set()
        for chunk in retrieved_chunks:
            source_key = (chunk.filename, chunk.page_number, chunk.section)
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "filename": chunk.filename,
                    "file_type": chunk.file_type,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "score": chunk.score,
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "text": chunk.text,
                })

        # Step 5: Prompt Construction & LLM Generation
        prompt = self._build_prompt(user_query, retrieved_chunks)
        llm_answer = self.llm.generate(prompt)

        # Determine if answer is considered grounded
        is_grounded = INSUFFICIENT_INFO_RESPONSE not in llm_answer

        # Step 6: Update conversational memory
        self.conversation_history.append(
            ConversationTurn(role="user", content=user_query)
        )
        self.conversation_history.append(
            ConversationTurn(
                role="assistant", content=llm_answer, sources=sources
            )
        )

        elapsed = round(time.time() - start_time, 3)
        return RAGResponse(
            answer=llm_answer,
            sources=sources,
            retrieved_chunks=retrieved_chunks,
            query=user_query,
            is_grounded=is_grounded,
            retrieval_confidence=top_score,
            execution_time=elapsed,
        )
