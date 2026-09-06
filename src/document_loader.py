"""
document_loader.py - Enterprise Document Ingestion & Extraction

Supports PDF and DOCX documents with metadata preservation:
- Filename
- Page number (1-indexed)
- Section / Heading if detected
- Document ID and hash
- Error handling for corrupt or empty documents
"""

import hashlib
import io
import os
import re
from dataclasses import dataclass, field
from typing import BinaryIO, Dict, List, Optional, Union

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import docx
except ImportError:
    docx = None


@dataclass
class Document:
    """Represents an extracted unit of text from an enterprise document."""
    content: str
    metadata: Dict[str, Union[str, int, float]] = field(default_factory=dict)

    @property
    def filename(self) -> str:
        return str(self.metadata.get("filename", "unknown"))

    @property
    def page_number(self) -> int:
        return int(self.metadata.get("page_number", 1))

    @property
    def section(self) -> str:
        return str(self.metadata.get("section", "General"))

    @property
    def doc_id(self) -> str:
        return str(self.metadata.get("doc_id", "doc_default"))


class DocumentLoader:
    """Enterprise document loader with cleaning, page tracking, and metadata tagging."""

    def __init__(self):
        pass

    @staticmethod
    def _generate_doc_id(filename: str, content_sample: str) -> str:
        """Generates a stable unique hash identifier for a document."""
        seed = f"{filename}_{content_sample[:200]}".encode("utf-8")
        return hashlib.md5(seed).hexdigest()[:12]

    @staticmethod
    def clean_text(raw_text: str) -> str:
        """
        Cleans raw extracted text:
        - Normalizes line breaks and whitespace
        - Strips null characters
        - Removes redundant spacing while preserving structure
        """
        if not raw_text:
            return ""

        # Remove null characters and non-printable control characters
        cleaned = raw_text.replace("\x00", " ")
        cleaned = re.sub(r"[\r\t]+", " ", cleaned)

        # Normalize consecutive spaces to single space, but preserve double newlines
        lines = [line.strip() for line in cleaned.split("\n")]
        # Group lines with content
        cleaned_lines = []
        for line in lines:
            line_clean = re.sub(r" {2,}", " ", line)
            cleaned_lines.append(line_clean)

        # Re-join, squashing excessive blank lines (> 2) into 2
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    def load_pdf(
        self,
        source: Union[str, BinaryIO, bytes, io.BytesIO],
        filename: str = "document.pdf"
    ) -> List[Document]:
        """
        Extracts text from a PDF file preserving per-page metadata.
        Accepts file paths or in-memory byte streams (e.g. Streamlit UploadedFile).
        """
        if pypdf is None:
            raise ImportError("pypdf is required to process PDF files. Please install pypdf.")

        docs: List[Document] = []
        try:
            if isinstance(source, (str, os.PathLike)):
                filename = os.path.basename(str(source))
                reader = pypdf.PdfReader(str(source))
            elif isinstance(source, bytes):
                reader = pypdf.PdfReader(io.BytesIO(source))
            else:
                reader = pypdf.PdfReader(source)

            total_pages = len(reader.pages)
            if total_pages == 0:
                return docs

            # Preview content to generate document ID
            sample_content = ""
            for p in reader.pages[: min(3, total_pages)]:
                extracted = p.extract_text() or ""
                sample_content += extracted
            doc_id = self._generate_doc_id(filename, sample_content)

            for page_idx, page in enumerate(reader.pages):
                raw_text = page.extract_text() or ""
                cleaned = self.clean_text(raw_text)

                if not cleaned:
                    continue

                # Basic heuristic to detect section header in the page
                first_lines = [l for l in cleaned.split("\n") if l.strip()]
                section = first_lines[0][:60] if first_lines else "General"

                metadata = {
                    "filename": filename,
                    "file_type": "pdf",
                    "page_number": page_idx + 1,
                    "total_pages": total_pages,
                    "section": section,
                    "doc_id": doc_id,
                    "char_count": len(cleaned),
                }
                docs.append(Document(content=cleaned, metadata=metadata))

        except Exception as e:
            raise RuntimeError(f"Error extracting PDF '{filename}': {str(e)}") from e

        return docs

    def load_docx(
        self,
        source: Union[str, BinaryIO, bytes, io.BytesIO],
        filename: str = "document.docx"
    ) -> List[Document]:
        """
        Extracts text from a DOCX file preserving section headings and metadata.
        """
        if docx is None:
            raise ImportError("python-docx is required to process DOCX files. Please install python-docx.")

        docs: List[Document] = []
        try:
            if isinstance(source, (str, os.PathLike)):
                filename = os.path.basename(str(source))
                doc_obj = docx.Document(str(source))
            elif isinstance(source, bytes):
                doc_obj = docx.Document(io.BytesIO(source))
            else:
                doc_obj = docx.Document(source)

            # Accumulate paragraphs, grouping by Headings
            current_section = "Introduction"
            paragraphs: List[str] = []
            page_estimate = 1
            char_accumulator = 0
            WORDS_PER_PAGE_ESTIMATE = 450

            all_text_for_id = " ".join(p.text for p in doc_obj.paragraphs[:10])
            doc_id = self._generate_doc_id(filename, all_text_for_id)

            for para in doc_obj.paragraphs:
                p_text = self.clean_text(para.text)
                if not p_text:
                    continue

                # Check if paragraph style is a Heading
                style_name = para.style.name if para.style else ""
                if "Heading" in style_name or (len(p_text) < 60 and p_text.isupper()):
                    if paragraphs:
                        # Flush current section as a document unit
                        combined = "\n\n".join(paragraphs)
                        metadata = {
                            "filename": filename,
                            "file_type": "docx",
                            "page_number": page_estimate,
                            "section": current_section,
                            "doc_id": doc_id,
                            "char_count": len(combined),
                        }
                        docs.append(Document(content=combined, metadata=metadata))
                        paragraphs = []
                    current_section = p_text

                paragraphs.append(p_text)
                char_accumulator += len(p_text)
                if char_accumulator > (WORDS_PER_PAGE_ESTIMATE * 5):
                    page_estimate += 1
                    char_accumulator = 0

            # Flush final section
            if paragraphs:
                combined = "\n\n".join(paragraphs)
                metadata = {
                    "filename": filename,
                    "file_type": "docx",
                    "page_number": page_estimate,
                    "section": current_section,
                    "doc_id": doc_id,
                    "char_count": len(combined),
                }
                docs.append(Document(content=combined, metadata=metadata))

        except Exception as e:
            raise RuntimeError(f"Error extracting DOCX '{filename}': {str(e)}") from e

        return docs

    def load_document(
        self,
        source: Union[str, BinaryIO, bytes, io.BytesIO],
        filename: Optional[str] = None
    ) -> List[Document]:
        """Loads a document detecting format by extension."""
        fname = filename or (os.path.basename(source) if isinstance(source, (str, os.PathLike)) else "unknown")
        ext = os.path.splitext(fname)[1].lower()

        if ext == ".pdf":
            return self.load_pdf(source, filename=fname)
        elif ext in [".docx", ".doc"]:
            return self.load_docx(source, filename=fname)
        else:
            # Fallback for text files or unsupported formats
            try:
                if isinstance(source, (str, os.PathLike)):
                    with open(source, "r", encoding="utf-8", errors="ignore") as f:
                        raw = f.read()
                elif isinstance(source, bytes):
                    raw = source.decode("utf-8", errors="ignore")
                else:
                    raw = source.read().decode("utf-8", errors="ignore")

                cleaned = self.clean_text(raw)
                if not cleaned:
                    return []
                doc_id = self._generate_doc_id(fname, cleaned)
                return [
                    Document(
                        content=cleaned,
                        metadata={
                            "filename": fname,
                            "file_type": "text",
                            "page_number": 1,
                            "section": "General",
                            "doc_id": doc_id,
                            "char_count": len(cleaned),
                        },
                    )
                ]
            except Exception as e:
                raise ValueError(f"Unsupported or unreadable file format '{fname}': {str(e)}")

    def load_directory(self, dir_path: str) -> List[Document]:
        """Loads all PDF and DOCX documents in a directory."""
        if not os.path.isdir(dir_path):
            return []

        all_docs: List[Document] = []
        for root, _, files in os.walk(dir_path):
            for file in sorted(files):
                if file.startswith(".") or file.startswith("~$"):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in [".pdf", ".docx", ".txt"]:
                    full_path = os.path.join(root, file)
                    try:
                        docs = self.load_document(full_path, filename=file)
                        all_docs.extend(docs)
                    except Exception as err:
                        print(f"Warning: Failed to load {file}: {err}")
        return all_docs
