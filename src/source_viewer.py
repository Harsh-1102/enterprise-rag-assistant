"""
source_viewer.py - Reusable Generic Enterprise Source Navigation & Viewer

Provides dynamic, metadata-driven source resolution and document viewing for:
- PDF: Interactive in-app page viewer navigating directly to cited page (#page=N)
- DOCX: Rich section & context preview with retrieved chunk highlighting
- Generic resolution without hardcoding any filenames
- Path traversal protection & Streamlit Community Cloud session persistence
"""

import base64
import io
import os
from typing import Any, Dict, List, Optional
import streamlit as st

# Safe directories allowed for document resolution
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(BASE_DIR, "data", "documents")
UPLOADS_DIR = os.path.join(DOCS_DIR, "uploads")

os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)


def get_safe_filename(raw_filename: str) -> str:
    """Sanitizes filename and prevents directory traversal attacks."""
    clean_name = os.path.basename(raw_filename).strip()
    # Strip null bytes and illegal characters
    clean_name = clean_name.replace("\x00", "").replace("/", "").replace("\\", "")
    return clean_name or "document"


def save_uploaded_document(file_bytes: bytes, filename: str) -> str:
    """
    Safely persists an uploaded file to disk and session cache so it remains
    available for viewing throughout the session, including on Streamlit Cloud.
    """
    safe_name = get_safe_filename(filename)
    target_path = os.path.join(UPLOADS_DIR, safe_name)

    try:
        with open(target_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"Warning: Failed to save upload to disk: {e}")

    # Also store in Streamlit session state registry for instant in-memory access
    if "doc_memory_registry" not in st.session_state:
        st.session_state["doc_memory_registry"] = {}
    st.session_state["doc_memory_registry"][safe_name] = file_bytes

    return target_path


def resolve_source(filename: str, doc_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Generic source resolver based on source metadata.
    Searches:
    1. Session in-memory cache (for active uploads on Streamlit Cloud)
    2. data/documents/uploads/
    3. data/documents/
    Never hardcodes filenames; validates against path traversal.
    """
    safe_name = get_safe_filename(filename)
    ext = os.path.splitext(safe_name)[1].lower().replace(".", "")
    file_type = "pdf" if ext == "pdf" else "docx" if ext in ["docx", "doc"] else "text"

    # 1. Check in-memory session registry
    mem_registry = st.session_state.get("doc_memory_registry", {})
    if safe_name in mem_registry:
        raw_bytes = mem_registry[safe_name]
        total_pages = _count_pdf_pages(raw_bytes) if file_type == "pdf" else 1
        return {
            "filename": safe_name,
            "file_type": file_type,
            "bytes": raw_bytes,
            "file_path": None,
            "total_pages": total_pages,
            "exists": True,
            "source_origin": "session_memory"
        }

    # 2. Check candidate disk paths
    candidate_paths = [
        os.path.join(UPLOADS_DIR, safe_name),
        os.path.join(DOCS_DIR, safe_name),
    ]

    for cpath in candidate_paths:
        abs_cpath = os.path.abspath(cpath)
        # Security: ensure resolved path is strictly inside allowed project directory
        if abs_cpath.startswith(DOCS_DIR) and os.path.isfile(abs_cpath):
            try:
                with open(abs_cpath, "rb") as f:
                    raw_bytes = f.read()
                total_pages = _count_pdf_pages(raw_bytes) if file_type == "pdf" else 1
                return {
                    "filename": safe_name,
                    "file_type": file_type,
                    "bytes": raw_bytes,
                    "file_path": abs_cpath,
                    "total_pages": total_pages,
                    "exists": True,
                    "source_origin": "disk"
                }
            except Exception as e:
                print(f"Warning: Error reading resolved file {abs_cpath}: {e}")

    # Fallback if binary file not found on disk or memory
    return {
        "filename": safe_name,
        "file_type": file_type,
        "bytes": None,
        "file_path": None,
        "total_pages": 1,
        "exists": False,
        "source_origin": "missing"
    }


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    """Helper to count total pages in a PDF byte stream."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        return len(reader.pages)
    except Exception:
        return 1


def validate_page_number(page_number: Any, total_pages: int = 1) -> int:
    """Validates and bounds page numbers safely."""
    try:
        p = int(page_number)
        if p < 1:
            return 1
        if total_pages > 0 and p > total_pages:
            return total_pages
        return p
    except (ValueError, TypeError):
        return 1


def render_pdf_viewer(
    source_info: Dict[str, Any],
    target_page: int,
    chunk_text: Optional[str] = None,
    section: Optional[str] = None
):
    """
    Renders an in-app PDF viewer navigated directly to the exact cited page.
    Uses base64 data URI with #page=N parameter.
    """
    filename = source_info["filename"]
    pdf_bytes = source_info.get("bytes")
    total_pages = source_info.get("total_pages", 1)
    safe_page = validate_page_number(target_page, total_pages)

    st.markdown(f"### 📄 `{filename}`")
    st.markdown(
        f"**Cited Page:** `{safe_page}` of `{total_pages}` "
        + (f"| **Section:** `{section}`" if section else "")
    )

    if not pdf_bytes:
        st.warning(
            f"The binary PDF file `{filename}` is not available in local storage. "
            "Showing indexed chunk text below:"
        )
        if chunk_text:
            st.info(chunk_text)
        return

    # Base64 data URI for direct browser rendering
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    data_uri = f"data:application/pdf;base64,{b64_pdf}#page={safe_page}&view=FitH&toolbar=1"

    # Action bar
    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button(
            label="⬇️ Download Document",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True
        )
    with c2:
        # Direct new tab link using standard data URI
        st.markdown(
            f"""
            <a href="{data_uri}" target="_blank" rel="noopener noreferrer" style="text-decoration: none;">
                <div style="background-color: #0f766e; color: white; text-align: center; padding: 7px 14px; border-radius: 8px; font-weight: 500; font-size: 0.88rem;">
                    ↗️ Open PDF in New Tab (#page={safe_page})
                </div>
            </a>
            """,
            unsafe_allow_html=True
        )

    st.write("")

    # Embedded in-app PDF Viewer iframe
    pdf_display_html = f"""
    <div style="border: 1px solid #cbd5e1; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
        <iframe 
            src="{data_uri}" 
            width="100%" 
            height="580px" 
            type="application/pdf"
            style="border: none; display: block;"
        >
            <p>Your browser does not support embedded PDF viewing. 
            <a href="{data_uri}" target="_blank">Click here to open the PDF directly.</a></p>
        </iframe>
    </div>
    """
    st.markdown(pdf_display_html, unsafe_allow_html=True)

    # Highlight retrieved evidence snippet
    if chunk_text:
        with st.expander("🔎 View Retrieved Evidence Passage on this Page", expanded=True):
            st.markdown(
                f"<div style='background: #f8fafc; border-left: 4px solid #0f766e; padding: 12px; border-radius: 4px; font-size: 0.9rem; color: #1e293b; line-height: 1.5;'>"
                f"{chunk_text}"
                f"</div>",
                unsafe_allow_html=True
            )


def render_docx_preview(
    source_info: Dict[str, Any],
    section: Optional[str] = None,
    chunk_text: Optional[str] = None
):
    """
    Renders structured section & context preview for DOCX files.
    DOCX files do not have reliable fixed print pages, so it renders verified section content.
    """
    filename = source_info["filename"]
    docx_bytes = source_info.get("bytes")

    st.markdown(f"### 📑 `{filename}`")
    st.caption("Document Format: Microsoft Word (DOCX) — Structured Section Preview")
    if section:
        st.markdown(f"**Verified Section:** `{section}`")

    if docx_bytes:
        # Download button for DOCX
        st.download_button(
            label="⬇️ Download DOCX File",
            data=docx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    st.markdown(
        """
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 14px; font-size: 0.82rem; color: #166534; margin: 10px 0;">
            ℹ️ <b>DOCX Layout Notice:</b> Word documents possess flowing layouts without fixed PDF page coordinates. 
            The exact semantic section and verified text chunk retrieved from this document are shown below.
        </div>
        """,
        unsafe_allow_html=True
    )

    if chunk_text:
        st.markdown("#### 🎯 Retrieved Source Text Chunk:")
        st.markdown(
            f"<div style='background: #ffffff; border: 1px solid #cbd5e1; border-left: 4px solid #0f766e; padding: 14px; border-radius: 6px; font-size: 0.92rem; color: #1e293b; line-height: 1.6;'>"
            f"{chunk_text}"
            f"</div>",
            unsafe_allow_html=True
        )

    # If full DOCX is available, parse paragraphs to show surrounding section text
    if docx_bytes:
        try:
            import docx
            doc = docx.Document(io.BytesIO(docx_bytes))
            all_paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            with st.expander("📖 Browse Full Document Text Content", expanded=False):
                for p_idx, para in enumerate(all_paras, 1):
                    if section and section.lower() in para.lower():
                        st.markdown(f"**📌 {para}**")
                    else:
                        st.markdown(f"• {para}")
        except Exception as e:
            print(f"Notice: Could not parse full DOCX paragraphs: {e}")


# Dialog modal viewer for modern Streamlit (Streamlit >= 1.34)
if hasattr(st, "dialog"):
    @st.dialog("📄 Enterprise Source Inspector", width="large")
    def _open_source_dialog(source_data: Dict[str, Any]):
        """Displays source inspector modal dialog."""
        _render_source_body(source_data)
else:
    def _open_source_dialog(source_data: Dict[str, Any]):
        # Fallback for environments without st.dialog
        st.session_state["active_viewer_source"] = source_data


def _render_source_body(source_data: Dict[str, Any]):
    """Internal helper to render either PDF or DOCX viewer body."""
    filename = source_data.get("filename", "document")
    file_type = source_data.get("file_type", "pdf" if filename.lower().endswith(".pdf") else "docx")
    page_number = source_data.get("page_number", 1)
    section = source_data.get("section", "General")
    chunk_text = source_data.get("text", "")

    resolved = resolve_source(filename, doc_id=source_data.get("doc_id"))
    if not resolved:
        st.error(f"Could not locate document source `{filename}`.")
        return

    if file_type == "pdf":
        render_pdf_viewer(
            resolved,
            target_page=page_number,
            chunk_text=chunk_text,
            section=section
        )
    else:
        render_docx_preview(
            resolved,
            section=section,
            chunk_text=chunk_text
        )


def trigger_source_viewer(source_data: Dict[str, Any]):
    """Opens the source viewer either via dialog or inline container."""
    if hasattr(st, "dialog"):
        _open_source_dialog(source_data)
    else:
        st.session_state["active_viewer_source"] = source_data
        st.rerun()


def render_source_cards(
    sources: List[Dict[str, Any]],
    key_prefix: str = "src",
    header_title: str = "📚 Verified Sources"
):
    """
    Unified reusable Streamlit component that renders interactive source citations.
    Works globally for ANY document (PDF, DOCX, custom user uploads).
    Never hardcodes filenames.
    """
    if not sources:
        return

    st.markdown(f"**{header_title}**")

    # Responsive grid layout: chunk into rows of at most 3 cards for clean display
    num_cols = min(max(len(sources), 1), 3)
    cols = st.columns(num_cols)

    for idx, s in enumerate(sources):
        col = cols[idx % num_cols]
        filename = s.get("filename", "Unknown")
        file_type = s.get(
            "file_type",
            "pdf" if filename.lower().endswith(".pdf") else "docx" if filename.lower().endswith(".docx") else "text"
        )
        page = s.get("page_number", 1)
        section = s.get("section", "General")
        score = s.get("score", 0.0)

        with col:
            is_pdf = (file_type == "pdf")
            icon = "📄" if is_pdf else "📑"
            if is_pdf:
                meta_label = f"Page {page} | Similarity: <b>{score:.2f}</b>"
                button_label = f"📄 Open Exact Source (P.{page})"
            else:
                sec_disp = section if len(section) <= 24 else section[:21] + "..."
                meta_label = f"Section: {sec_disp} | Similarity: <b>{score:.2f}</b>"
                button_label = "📑 Open Source Context"

            st.markdown(
                f"""
                <div style="background: #ffffff; border: 1px solid #cbd5e1; border-top: 3px solid #0f766e; border-radius: 8px; padding: 12px; margin-bottom: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
                    <div style="font-weight: 600; font-size: 0.88rem; color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{filename}">
                        {icon} {filename}
                    </div>
                    <div style="font-size: 0.80rem; color: #475569; margin-top: 5px;">
                        {meta_label}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            button_key = f"{key_prefix}_btn_{idx}_{filename}_{page}_{s.get('chunk_id', idx)}"
            if st.button(button_label, key=button_key, use_container_width=True, type="secondary"):
                trigger_source_viewer(s)


def trigger_source_viewer(source_data: Dict[str, Any]):
    """Opens the source viewer either via dialog or inline container."""
    st.session_state["active_viewer_source"] = source_data
    if hasattr(st, "dialog"):
        _open_source_dialog(source_data)


def render_fallback_inline_viewer():
    """Renders active source viewer inline container when a source is selected."""
    if "active_viewer_source" in st.session_state and st.session_state["active_viewer_source"]:
        source_data = st.session_state["active_viewer_source"]
        with st.container():
            st.markdown("---")
            c_hdr, c_close = st.columns([5, 1])
            with c_hdr:
                st.markdown(f"#### 🔍 Document Source Inspector: `{source_data.get('filename')}`")
            with c_close:
                if st.button("✖️ Close Viewer", key="close_active_inline_viewer", use_container_width=True):
                    st.session_state["active_viewer_source"] = None
                    st.rerun()
            _render_source_body(source_data)
            st.markdown("---")

