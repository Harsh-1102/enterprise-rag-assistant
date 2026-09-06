"""
test_source_navigation.py
Automated verification test suite for Generic Clickable Source Navigation in RAG Assistant.
"""

import os
import sys
import dotenv
dotenv.load_dotenv()

from src.rag_pipeline import RAGPipeline
from src.source_viewer import resolve_source, validate_page_number, save_uploaded_document, get_safe_filename

def run_tests():
    print("=" * 70)
    print("🚀 RUNNING SOURCE NAVIGATION VERIFICATION SUITE")
    print("=" * 70)

    # 1. Security & Sanitization Tests
    print("\n--- Test 1: Path Traversal & Security Validation ---")
    unsafe_filenames = [
        "../../etc/passwd",
        "/etc/shadow",
        "../../app.py",
        "../..\\Windows\\System32\\cmd.exe",
        "Leave_Policy.pdf\x00.exe"
    ]
    for bad_name in unsafe_filenames:
        safe = get_safe_filename(bad_name)
        res = resolve_source(bad_name)
        print(f"Malicious path: {bad_name:35} -> Safe: {safe:20} -> Exists in store: {res['exists']}")
        assert "/" not in safe and "\\" not in safe, f"Security breach: {safe}"
    print("✅ Path traversal prevention PASSED!")

    # 2. Dynamic Source Resolution for all 9 Bundled Documents
    print("\n--- Test 2: Dynamic Source Resolver for All Documents ---")
    required_docs = [
        ("Leave_Policy.pdf", "pdf", 2),
        ("Employee_Handbook.pdf", "pdf", 3),
        ("Work_From_Home_Policy.pdf", "pdf", 2),
        ("Employee_Benefits.pdf", "pdf", 2),
        ("Attendance_Policy.pdf", "pdf", 2),
        ("Code_of_Conduct.pdf", "pdf", 2),
        ("Resignation_and_Notice_Period.pdf", "pdf", 2),
        ("Attendance_Policy.docx", "docx", 1),
        ("Code_Of_Conduct.docx", "docx", 1),
    ]

    for fname, expected_type, min_pages in required_docs:
        info = resolve_source(fname)
        assert info is not None, f"Failed to resolve {fname}"
        assert info["exists"] is True, f"Document {fname} not found on disk/memory"
        assert info["file_type"] == expected_type, f"Expected {expected_type}, got {info['file_type']}"
        assert info["bytes"] is not None and len(info["bytes"]) > 0, f"No bytes loaded for {fname}"
        if expected_type == "pdf":
            assert info["total_pages"] >= min_pages, f"Expected >= {min_pages} pages for {fname}, got {info['total_pages']}"
        print(f"  ✓ {fname:35} | Type: {info['file_type']:4} | Pages: {info['total_pages']} | Size: {len(info['bytes'])} bytes")
    print("✅ All 9 documents dynamically resolved with correct types & pages!")

    # 3. Dynamic Upload & Session Cache Resolution (Streamlit Cloud simulation)
    print("\n--- Test 3: Session In-Memory Cache (Streamlit Cloud Compatibility) ---")
    fake_doc_name = "New_Vendor_Agreement_2026.pdf"
    fake_doc_bytes = b"%PDF-1.4 Mock PDF Content For Cloud Test"
    # Call save_uploaded_document
    saved_path = save_uploaded_document(fake_doc_bytes, fake_doc_name)
    resolved_upload = resolve_source(fake_doc_name)
    assert resolved_upload["exists"] is True
    assert resolved_upload["bytes"] == fake_doc_bytes
    print(f"  ✓ Uploaded document {fake_doc_name} successfully resolved from registry!")
    print("✅ Streamlit Cloud session cache test PASSED!")

    # 4. Multi-Document RAG Retrieval Test
    print("\n--- Test 4: RAG Retrieval Across Diverse Documents ---")
    pipeline = RAGPipeline(index_dir="vectorstore")
    pipeline.retriever.load()
    assert pipeline.retriever.is_indexed(), "FAISS vectorstore is not indexed!"

    test_queries = [
        {
            "target": "Leave_Policy.pdf Page 1",
            "query": "What is the annual paid leave entitlement for full-time employees?",
            "expected_file": "Leave_Policy.pdf",
            "expected_page": 1,
        },
        {
            "target": "Leave_Policy.pdf Page 2",
            "query": "What is the maximum consecutive days of sick leave without a doctor certificate?",
            "expected_file": "Leave_Policy.pdf",
            "expected_page": 2,
        },
        {
            "target": "Employee_Handbook.pdf",
            "query": "What is the standard probation period and core working hours in the Employee Handbook?",
            "expected_file": "Employee_Handbook.pdf",
            "expected_page": None,
        },
        {
            "target": "Work_From_Home_Policy.pdf",
            "query": "What are the core hours and monthly internet reimbursement for remote work?",
            "expected_file": "Work_From_Home_Policy.pdf",
            "expected_page": 1,
        },
        {
            "target": "Employee_Benefits.pdf",
            "query": "What health, dental and vision insurance coverage maximum is provided to employees?",
            "expected_file": "Employee_Benefits.pdf",
            "expected_page": None,
        },
        {
            "target": "Code_of_Conduct.pdf",
            "query": "What is the zero tolerance policy on harassment and ethics reporting hotline?",
            "expected_file": "Code_of_Conduct.pdf",
            "expected_page": None,
        },
        {
            "target": "Resignation_and_Notice_Period.pdf",
            "query": "What is the notice period for resignation of permanent staff and probation staff?",
            "expected_file": "Resignation_and_Notice_Period.pdf",
            "expected_page": 1,
        },
        {
            "target": "DOCX source (Attendance_Policy.docx)",
            "query": "What are the attendance recording rules, tardiness grace periods and biometric check-in?",
            "expected_file": "Attendance_Policy.docx",
            "expected_page": None,
        },
    ]

    for t in test_queries:
        print(f"\nTesting Query: '{t['query']}'")
        res = pipeline.query(t["query"], top_k=3, similarity_threshold=0.30)
        retrieved_files = [s["filename"] for s in res.sources]
        print(f"  Target: {t['target']}")
        print(f"  Retrieved Sources ({len(res.sources)}):")
        for s in res.sources:
            print(f"    • {s['filename']} (P.{s['page_number']}, Sec: '{s['section']}') — Cosine: {s['score']}")
            # Verify resolve_source works on every retrieved citation
            resolved = resolve_source(s["filename"], doc_id=s.get("doc_id"))
            assert resolved["exists"] is True, f"Failed to resolve retrieved source {s['filename']}"
            assert resolved["bytes"] is not None, f"Missing bytes for {s['filename']}"

            # Verify page bounds for PDFs
            if resolved["file_type"] == "pdf":
                valid_p = validate_page_number(s["page_number"], resolved["total_pages"])
                assert 1 <= valid_p <= resolved["total_pages"], f"Invalid page number {valid_p}"

        # Verify expected document is retrieved in top sources
        matched = any(t["expected_file"].lower() in rf.lower() for rf in retrieved_files)
        print(f"  Matched expected '{t['expected_file']}': {matched}")
        assert matched, f"Expected {t['expected_file']} in {retrieved_files}"

        if t["expected_page"] is not None:
            page_matched = any(s["filename"].lower() == t["expected_file"].lower() and s["page_number"] == t["expected_page"] for s in res.sources)
            print(f"  Matched expected Page {t['expected_page']}: {page_matched}")

    print("\n" + "=" * 70)
    print("🎉 ALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
