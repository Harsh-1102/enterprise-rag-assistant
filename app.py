"""
app.py - Enterprise Document Intelligence & RAG Assistant
Streamlit Web Application
"""

import os
import time
from typing import List

import streamlit as st
import dotenv

# Load environment variables
dotenv.load_dotenv()

from src.document_loader import Document, DocumentLoader
from src.chunking import DocumentChunker
from src.embeddings import EmbeddingManager
from src.retriever import FAISSRetriever
from src.rag_pipeline import RAGPipeline, INSUFFICIENT_INFO_RESPONSE
from src.evaluation import RAGEvaluator, HR_BENCHMARK_DATASET

# ==============================================================================
# Page Configuration & Styling
# ==============================================================================
st.set_page_config(
    page_title="Enterprise AI Document Assistant",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Enterprise CSS Design System
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }

    /* Hero Header Card */
    .hero-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f766e 100%);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 24px;
        color: #ffffff;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.3), 0 8px 10px -6px rgba(15, 23, 42, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
        background: linear-gradient(to right, #ffffff, #a7f3d0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 0.98rem;
        color: #cbd5e1;
        margin-bottom: 12px;
        font-weight: 400;
        line-height: 1.5;
    }
    .domain-badge {
        display: inline-block;
        background: rgba(15, 118, 110, 0.4);
        border: 1px solid #14b8a6;
        color: #5eead4;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Metric Cards */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f766e;
    }
    .metric-lbl {
        font-size: 0.8rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* Source Cards */
    .source-tag {
        display: inline-flex;
        align-items: center;
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        color: #166534;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 500;
        margin: 3px;
        font-family: 'JetBrains Mono', monospace;
    }

    .grounded-badge {
        background: #ecfdf5;
        border: 1px solid #10b981;
        color: #065f46;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .fallback-badge {
        background: #fffbeb;
        border: 1px solid #f59e0b;
        color: #92400e;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Code & Previews */
    .chunk-box {
        background-color: #f8fafc;
        border-left: 3px solid #0f766e;
        padding: 12px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 8px;
        font-size: 0.85rem;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# Pipeline Cache & Session State
# ==============================================================================
@st.cache_resource(show_spinner=False)
def get_base_pipeline():
    """Initializes the persistent RAG pipeline singleton."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    pipeline = RAGPipeline(
        index_dir="vectorstore",
        embedding_model_name="all-MiniLM-L6-v2",
        chunk_size=500,
        chunk_overlap=60,
        gemini_api_key=api_key if api_key != "your_gemini_api_key_here" else None,
        similarity_threshold=0.35,
    )
    # Attempt to load pre-indexed vectorstore if exists
    pipeline.retriever.load()
    return pipeline


pipeline = get_base_pipeline()

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_doc_names" not in st.session_state:
    st.session_state.uploaded_doc_names = []
if "ingestion_done" not in st.session_state:
    st.session_state.ingestion_done = pipeline.retriever.is_indexed()


# ==============================================================================
# Sidebar - Configuration, Documents & Controls
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/briefcase.png", width=64)
    st.title("Enterprise Control Panel")
    st.markdown("---")

    # 1. LLM API Key Configuration
    st.subheader("🔑 Google Gemini LLM")
    current_key = os.getenv("GEMINI_API_KEY", "")
    if current_key == "your_gemini_api_key_here":
        current_key = ""

    user_api_key = st.text_input(
        "Enter Gemini API Key:",
        value=current_key,
        type="password",
        help="Get your key at: https://aistudio.google.com/app/apikey"
    )

    if user_api_key:
        pipeline.set_gemini_key(user_api_key)
        st.success("API Key Active", icon="✅")
    else:
        st.warning("API Key not set. Pipeline will run in local retrieval mode with context summarization.", icon="⚠️")

    st.markdown("---")

    # 2. Document Ingestion & Upload
    st.subheader("📂 Document Management")
    uploaded_files = st.file_uploader(
        "Upload Enterprise Documents:",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="Upload company policy PDFs, handbooks, or DOCX manuals."
    )

    # Pre-load sample synthetic documents option
    load_samples_btn = st.button("📁 Load Synthetic HR Policies", use_container_width=True)
    if load_samples_btn:
        sample_dir = os.path.join(os.path.dirname(__file__), "data", "documents")
        if os.path.isdir(sample_dir):
            with st.spinner("Loading synthetic HR documents from disk..."):
                docs = pipeline.loader.load_directory(sample_dir)
                if docs:
                    res = pipeline.ingest_documents(docs, force_rebuild=True)
                    st.session_state.ingestion_done = True
                    st.session_state.uploaded_doc_names = list(set([d.filename for d in docs]))
                    st.success(f"Indexed {res['num_documents']} documents into {res['num_chunks']} chunks!")
                    st.rerun()
                else:
                    st.error("No sample documents found. Run `python3 create_sample_docs.py` first.")
        else:
            st.error("Sample directory not found.")

    if uploaded_files:
        st.caption(f"Selected {len(uploaded_files)} file(s):")
        for f in uploaded_files:
            st.caption(f"• `{f.name}` ({round(f.size / 1024, 1)} KB)")

    col_idx, col_reidx = st.columns(2)
    with col_idx:
        index_btn = st.button("⚡ Index Docs", type="primary", use_container_width=True)
    with col_reidx:
        rebuild_btn = st.button("🔄 Re-Index", use_container_width=True)

    if (index_btn or rebuild_btn) and uploaded_files:
        with st.spinner("Extracting, cleaning, chunking, and embedding documents..."):
            all_docs: List[Document] = []
            for ufile in uploaded_files:
                try:
                    file_bytes = ufile.read()
                    docs = pipeline.loader.load_document(file_bytes, filename=ufile.name)
                    all_docs.extend(docs)
                except Exception as e:
                    st.error(f"Error parsing {ufile.name}: {e}")

            if all_docs:
                res = pipeline.ingest_documents(all_docs, force_rebuild=True)
                st.session_state.ingestion_done = True
                st.session_state.uploaded_doc_names = list(set([d.filename for d in all_docs]))
                st.success(f"Success! Indexed {res['num_documents']} documents ({res['num_chunks']} chunks).")
                st.rerun()

    st.markdown("---")

    # 3. Knowledge Base Status
    st.subheader("📊 Knowledge Base Stats")
    total_vectors = pipeline.retriever.total_vectors
    st.markdown(f"**Indexed Vectors in FAISS:** `{total_vectors}`")
    st.markdown(f"**Embedding Model:** `all-MiniLM-L6-v2 (384-D)`")
    st.markdown(f"**LLM Model:** `{pipeline.llm.model_name}`")

    st.markdown("---")

    # 4. Hyperparameter Controls
    st.subheader("⚙️ RAG Hyperparameters")
    top_k = st.slider("Top-K Retrieved Chunks:", min_value=1, max_value=8, value=4, step=1)
    similarity_threshold = st.slider(
        "Similarity Threshold (Cosine):",
        min_value=0.10,
        max_value=0.80,
        value=0.35,
        step=0.05,
        help="Chunks with similarity below this score are filtered to prevent hallucination."
    )
    chunk_size = st.slider("Chunk Size (Chars):", min_value=200, max_value=1000, value=500, step=50)
    chunk_overlap = st.slider("Chunk Overlap (Chars):", min_value=20, max_value=200, value=60, step=10)

    pipeline.update_chunking_config(chunk_size, chunk_overlap)
    pipeline.similarity_threshold = similarity_threshold

    st.markdown("---")

    # 5. Clear Memory
    if st.button("🗑️ Clear Conversation Memory", use_container_width=True):
        pipeline.clear_memory()
        st.session_state.messages = []
        st.toast("Conversational memory cleared!")
        st.rerun()


# ==============================================================================
# Main Interface Area
# ==============================================================================
st.markdown("""
<div class="hero-card">
    <div class="domain-badge">Domain: HR Intelligence Assistant</div>
    <div class="hero-title">ENTERPRISE AI DOCUMENT ASSISTANT</div>
    <div class="hero-subtitle">
        Enterprise-grade Retrieval-Augmented Generation (RAG) platform. 
        Ask natural language questions across verified HR policies, handbooks, and corporate documentation with guaranteed factual grounding and exact source attribution.
    </div>
</div>
""", unsafe_allow_html=True)

# Overview Metrics Row
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{pipeline.retriever.total_vectors}</div>
        <div class="metric-lbl">Vector Chunks</div>
    </div>
    """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{len(st.session_state.uploaded_doc_names) or (6 if pipeline.retriever.total_vectors > 0 else 0)}</div>
        <div class="metric-lbl">Loaded Documents</div>
    </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{top_k}</div>
        <div class="metric-lbl">Top-K Depth</div>
    </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-val">{similarity_threshold:.2f}</div>
        <div class="metric-lbl">Confidence Min</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Navigation Tabs
tab_chat, tab_eval, tab_arch = st.tabs(["💬 Query Assistant", "📈 Evaluation & Benchmark", "🏛️ Architecture & Pipeline"])


# ==============================================================================
# TAB 1: Conversational RAG Query Assistant
# ==============================================================================
with tab_chat:
    # Quick Test Question Chips
    st.markdown("**💡 Quick Test Questions:**")
    qc1, qc2, qc3, qc4, qc5 = st.columns(5)
    sample_question = None

    if qc1.button("🌴 Leave Entitlement", use_container_width=True):
        sample_question = "What is the annual paid leave entitlement for full-time employees?"
    if qc2.button("🤒 Sick Leave Rule", use_container_width=True):
        sample_question = "How many days of sick leave can I take without a doctor note?"
    if qc3.button("🏠 WFH Core Hours", use_container_width=True):
        sample_question = "What are the core working hours under the Work From Home policy?"
    if qc4.button("🚪 Resignation Notice", use_container_width=True):
        sample_question = "What is the resignation notice period for permanent staff?"
    if qc5.button("🚫 Out-of-Domain Test", use_container_width=True):
        sample_question = "What is the capital of France and what is its population?"

    st.markdown("---")

    # Render Conversation History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🧑‍💼" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

            # Render Sources and Chunks if present
            if msg.get("sources"):
                st.markdown("**📚 Verified Sources:**")
                source_html = " ".join([
                    f"<span class='source-tag'>📄 {s['filename']} (Page {s['page_number']}) — Cosine: {s['score']:.2f}</span>"
                    for s in msg["sources"]
                ])
                st.markdown(source_html, unsafe_allow_html=True)

            if msg.get("retrieved_chunks"):
                with st.expander("🔍 Inspect Retrieved Context Chunks (Top-K)"):
                    for idx, ch in enumerate(msg["retrieved_chunks"], 1):
                        st.markdown(f"""
                        <div class="chunk-box">
                            <b>Chunk #{idx}</b> | <code>{ch.filename}</code> (Page {ch.page_number}, Section: {ch.section}) | <b>Score: {ch.score:.3f}</b>
                            <br><br>
                            {ch.text}
                        </div>
                        """, unsafe_allow_html=True)

    # Chat Input Box
    user_input = st.chat_input("Ask any question about company HR policies, benefits, attendance, or handbook...")
    query_to_run = sample_question or user_input

    if query_to_run:
        # Check if vector store is populated
        if pipeline.retriever.total_vectors == 0:
            st.error("Knowledge base is empty! Please click 'Load Synthetic HR Policies' or upload documents in the sidebar first.")
        else:
            # Display user query in chat
            st.session_state.messages.append({"role": "user", "content": query_to_run})
            with st.chat_message("user", avatar="🧑‍💼"):
                st.markdown(query_to_run)

            # Generate RAG response
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Retrieving semantic context from FAISS and generating grounded answer..."):
                    rag_res = pipeline.query(
                        user_query=query_to_run,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold,
                    )

                # Grounding Badge
                if rag_res.is_grounded:
                    st.markdown(
                        f"<span class='grounded-badge'>✅ Grounded in Enterprise Context (Confidence: {rag_res.retrieval_confidence:.2f} | Latency: {rag_res.execution_time:.2f}s)</span>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<span class='fallback-badge'>⚠️ Insufficient Evidence / Out-of-Domain (Confidence: {rag_res.retrieval_confidence:.2f})</span>",
                        unsafe_allow_html=True
                    )

                st.markdown(rag_res.answer)

                # Sources Display
                if rag_res.sources:
                    st.markdown("**📚 Verified Sources:**")
                    source_html = " ".join([
                        f"<span class='source-tag'>📄 {s['filename']} (Page {s['page_number']}) — Cosine: {s['score']:.2f}</span>"
                        for s in rag_res.sources
                    ])
                    st.markdown(source_html, unsafe_allow_html=True)

                # Retrieved context expander
                if rag_res.retrieved_chunks:
                    with st.expander("🔍 Inspect Retrieved Context Chunks (Top-K)"):
                        for idx, ch in enumerate(rag_res.retrieved_chunks, 1):
                            st.markdown(f"""
                            <div class="chunk-box">
                                <b>Chunk #{idx}</b> | <code>{ch.filename}</code> (Page {ch.page_number}, Section: {ch.section}) | <b>Score: {ch.score:.3f}</b>
                                <br><br>
                                {ch.text}
                            </div>
                            """, unsafe_allow_html=True)

                # Record in session state
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": rag_res.answer,
                    "sources": rag_res.sources,
                    "retrieved_chunks": rag_res.retrieved_chunks,
                    "is_grounded": rag_res.is_grounded,
                    "confidence": rag_res.retrieval_confidence,
                })


# ==============================================================================
# TAB 2: RAG Evaluation & Benchmark Suite
# ==============================================================================
with tab_eval:
    st.subheader("📊 RAG Evaluation & Benchmarking System")
    st.markdown("""
    Academic evaluation suite measuring core RAG metrics:
    - **Hit Rate (Hit@K)**: Checks if the correct enterprise document was retrieved in the Top-K results.
    - **Answer Correctness (F1)**: Computes n-gram token overlap against the gold standard ground truth.
    - **Groundedness / Faithfulness**: Measures whether answer claims are strictly supported by the retrieved text.
    - **Hallucination Rate**: Detects if fabricated facts or unsupported answers were produced (especially on out-of-domain queries).
    """)

    if st.button("🚀 Run Complete Benchmark (9 Gold-Standard Questions)", type="primary"):
        if pipeline.retriever.total_vectors == 0:
            st.error("Please load or index documents first before running evaluation.")
        else:
            with st.spinner("Executing benchmark across in-domain and out-of-domain questions..."):
                evaluator = RAGEvaluator(pipeline)
                df_results, summary_metrics = evaluator.run_benchmark(HR_BENCHMARK_DATASET, top_k=top_k)

            st.success("Evaluation complete!")

            # Summary Metric Cards
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Hit@K Retrieval Rate", f"{summary_metrics['Retrieval Hit Rate (Hit@K)']}%")
            sm2.metric("Groundedness Score", f"{summary_metrics['Average Groundedness Score']}%")
            sm3.metric("Answer F1 Score", f"{summary_metrics['Average Answer F1']}%")
            sm4.metric("Hallucination Rate", f"{summary_metrics['Hallucination Rate']}%", delta="Target: 0%", delta_color="inverse")

            st.markdown("### 📋 Detailed Benchmark Results Table")
            display_cols = [
                "id", "question", "category", "expected_source",
                "retrieval_hit", "confidence_score", "groundedness", "answer_f1", "hallucination"
            ]
            st.dataframe(df_results[display_cols], use_container_width=True)

            csv_data = df_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Export Evaluation Results (CSV)",
                data=csv_data,
                file_name="rag_evaluation_results.csv",
                mime="text/csv",
            )


# ==============================================================================
# TAB 3: Architecture & Pipeline Documentation
# ==============================================================================
with tab_arch:
    st.subheader("🏛️ Enterprise RAG Architecture")
    st.markdown("""
    This project strictly implements a multi-stage **Retrieval-Augmented Generation (RAG)** pipeline:
    """)

    st.code("""
    [Enterprise Documents]
           │
           ▼
    [Document Loader: PyPDF / python-docx]
           │  (Extract text, clean whitespace, preserve filename & page numbers)
           ▼
    [Recursive Semantic Chunker]
           │  (Configurable Chunk Size: 500 chars, Overlap: 60 chars + metadata tagging)
           ▼
    [Dense Embeddings: Sentence-Transformers (all-MiniLM-L6-v2)]
           │  (384-dimensional unit-normalized dense vectors)
           ▼
    [Local Vector Database: FAISS IndexFlatIP]
           │  (Persistent index.faiss + metadata.pkl)
           │
     ◄─────┴───────────────────────────────────────────────────────┐
     │                                                             │
[User Query]                                                       │
     │                                                             │
     ▼                                                             │
[Query Embedding: all-MiniLM-L6-v2]                                │
     │ (Same embedding model)                                      │
     ▼                                                             │
[FAISS Cosine Similarity Search]                                   │
     │                                                             │
     ▼                                                             │
[Top-K Retrieved Chunks + Confidence Score Thresholding]           │
     │                                                             │
     ├─► [Below Threshold / Out-of-Domain?] ──► [Fallback Response (No Hallucination)]
     │
     ▼
[Strict Grounding Prompt + Multi-Turn Memory]
     │
     ▼
[Google Gemini 1.5 Flash LLM]
     │
     ▼
[Grounded Answer + Verified Source Attribution (Doc Name + Page)]
    """, language="text")

    st.markdown("### 🔑 Key Engineering Decisions")
    st.markdown("""
    1. **Identical Embedding Models**: `all-MiniLM-L6-v2` is used for both indexing chunks and encoding user queries, ensuring geometric consistency in vector space.
    2. **Unit Normalization + IndexFlatIP**: Vectors are normalized to unit length so that inner product equals exact cosine similarity with $O(1)$ computation per candidate.
    3. **Two-Tier Hallucination Prevention**:
       - *Tier 1 (Retriever Level)*: Similarity threshold filters out irrelevant chunks and catches out-of-domain queries.
       - *Tier 2 (Prompt Level)*: Strict negative constraints instruct the LLM never to guess or use external facts.
    4. **Conversational Memory**: Maintains dialogue context to handle follow-up queries like *"What about sick leave?"* without losing document grounding.
    """)
