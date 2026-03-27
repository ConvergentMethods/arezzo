"""Phase 4: Live MCP server validation — exercises server tool functions
against real Google Docs.

Unlike validate_live.py (which calls compile_operations directly), this
script exercises the server's tool functions (read_document, edit_document,
validate_operations) to validate the full MCP stack end-to-end.

Tests:
  1. read_document — structural map against a real document
  2. edit_document — compile + execute through server tool
  3. validate_operations — compile-only dry run
  4. edit_document error handling — invalid address, invalid operation

Usage:
    uv run validate_mcp.py
"""

import sys
import time

from auth import get_docs_service
from arezzo.server import read_document, edit_document, validate_operations


# ── Doc setup ───────────────────────────────────────────────────────────

def create_test_doc(service) -> str:
    """Create a scratch document and return its document_id."""
    text = (
        "Report Title\n"
        "Executive Summary\n"
        "This report covers quarterly performance metrics and key findings.\n"
        "Revenue Analysis\n"
        "Total revenue increased by 15% compared to the previous quarter.\n"
        "Key Metrics\n"
        "Monthly recurring revenue reached a new high.\n"
        "Conclusion\n"
        "The outlook for next quarter remains positive.\n"
    )
    doc = service.documents().create(body={"title": "arezzo_mcp_validation"}).execute()
    doc_id = doc["documentId"]

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
    ).execute()

    lines = text.split("\n")[:-1]
    offset = 1
    reqs = []
    h1 = ["Report Title"]
    h2 = ["Executive Summary", "Revenue Analysis", "Key Metrics", "Conclusion"]
    for line in lines:
        end = offset + len(line) + 1
        if line in h1:
            reqs.append({"updateParagraphStyle": {
                "range": {"startIndex": offset, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_1"},
                "fields": "namedStyleType"}})
        elif line in h2:
            reqs.append({"updateParagraphStyle": {
                "range": {"startIndex": offset, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType"}})
        offset = end

    service.documents().batchUpdate(
        documentId=doc_id, body={"requests": reqs}
    ).execute()
    time.sleep(0.5)
    return doc_id


def get_body_text(service, doc_id: str) -> str:
    doc = service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
    body = doc["tabs"][0]["documentTab"]["body"]["content"]
    parts = []
    for el in body:
        if "paragraph" in el:
            for elem in el["paragraph"].get("elements", []):
                tr = elem.get("textRun")
                if tr:
                    parts.append(tr.get("content", ""))
    return "".join(parts)


# ── Test cases ───────────────────────────────────────────────────────────

def test_read_document(doc_id: str) -> bool:
    """read_document returns a correct structural map."""
    result = read_document(doc_id)

    try:
        assert "next_step" in result, "Missing next_step"
        assert "document_reality" in result, "Missing document_reality"
        reality = result["document_reality"]
        assert reality["document_id"] == doc_id, "document_id mismatch"

        headings = reality["headings"]
        assert len(headings) == 5, f"Expected 5 headings, got {len(headings)}"
        heading_texts = {h["text"] for h in headings}
        assert "Report Title" in heading_texts
        assert "Revenue Analysis" in heading_texts

        # Verify levels
        by_text = {h["text"]: h["level"] for h in headings}
        assert by_text["Report Title"] == 1
        assert by_text["Executive Summary"] == 2

        # next_step mentions headings
        assert "edit_document" in result["next_step"]
        assert "headings" in result["next_step"]

        print("  test_read_document: PASS")
        return True
    except AssertionError as e:
        print(f"  test_read_document: FAIL — {e}")
        return False


def test_edit_document_insert(service, doc_id: str) -> bool:
    """edit_document compiles and executes an insert operation."""
    ops = [{
        "type": "insert_text",
        "address": {"heading": "Revenue Analysis"},
        "params": {"text": "MCP LAYER VALIDATION PASS.\n"},
    }]
    result = edit_document(doc_id, ops)

    try:
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert result["operations_compiled"] == 1
        assert result["requests_emitted"] == 1
        assert "Document updated" in result["next_step"]

        # Verify mutation in live document
        time.sleep(0.3)
        text = get_body_text(service, doc_id)
        assert "MCP LAYER VALIDATION PASS." in text

        ra_idx = text.index("Revenue Analysis")
        ins_idx = text.index("MCP LAYER VALIDATION PASS.")
        assert ins_idx > ra_idx, "Inserted text should appear after heading"

        print("  test_edit_document_insert: PASS")
        return True
    except AssertionError as e:
        print(f"  test_edit_document_insert: FAIL — {e}")
        return False


def test_edit_document_compound(service, doc_id: str) -> bool:
    """edit_document with compound op (insert_table) returns present_to_user."""
    read_result = read_document(doc_id)
    headings = read_result["document_reality"]["headings"]
    key_metrics = next((h for h in headings if h["text"] == "Key Metrics"), None)
    assert key_metrics is not None, "Key Metrics heading not found"

    ops = [{
        "type": "insert_table",
        "address": {"index": key_metrics["end_index"]},
        "params": {"rows": 2, "columns": 3},
    }]
    result = edit_document(doc_id, ops)

    try:
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        assert "present_to_user" in result, "Compound op should set present_to_user"
        assert "read_document" in result["next_step"]

        # Verify table exists in live document
        time.sleep(0.3)
        doc = service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
        body = doc["tabs"][0]["documentTab"]["body"]["content"]
        tables = [el for el in body if "table" in el]
        assert len(tables) >= 1, f"Expected at least 1 table, got {len(tables)}"

        print("  test_edit_document_compound: PASS")
        return True
    except AssertionError as e:
        print(f"  test_edit_document_compound: FAIL — {e}")
        return False


def test_validate_operations(doc_id: str) -> bool:
    """validate_operations returns compiled requests without executing."""
    ops = [{
        "type": "insert_text",
        "address": {"heading": "Conclusion"},
        "params": {"text": "VALIDATION ONLY — NOT EXECUTED.\n"},
    }]
    result = validate_operations(doc_id, ops)

    try:
        assert result["validation"] == "passed"
        assert result["operations_compiled"] == 1
        assert result["requests_emitted"] == 1
        assert result["content_mutations"] == 1
        assert "compiled_requests" in result
        assert "edit_document" in result["next_step"]

        print("  test_validate_operations: PASS")
        return True
    except AssertionError as e:
        print(f"  test_validate_operations: FAIL — {e}")
        return False


def test_error_invalid_address(doc_id: str) -> bool:
    """edit_document returns structured error for unknown heading."""
    ops = [{
        "type": "insert_text",
        "address": {"heading": "NO_SUCH_HEADING_XYZ"},
        "params": {"text": "Should not appear.\n"},
    }]
    result = edit_document(doc_id, ops)

    try:
        assert result.get("error") == "address_resolution_failed"
        assert "next_step" in result
        assert "read_document" in result["next_step"]

        print("  test_error_invalid_address: PASS")
        return True
    except AssertionError as e:
        print(f"  test_error_invalid_address: FAIL — {e}")
        return False


def test_error_invalid_operation(doc_id: str) -> bool:
    """edit_document returns structured error for unknown operation type."""
    ops = [{"type": "not_a_real_operation", "address": {"start": True}, "params": {}}]
    result = edit_document(doc_id, ops)

    try:
        assert result.get("error") in ("invalid_operation", "compilation_failed")
        assert "next_step" in result

        print("  test_error_invalid_operation: PASS")
        return True
    except AssertionError as e:
        print(f"  test_error_invalid_operation: FAIL — {e}")
        return False


# ── Runner ───────────────────────────────────────────────────────────────

def main():
    service = get_docs_service()
    print("Creating test document...")
    doc_id = create_test_doc(service)
    print(f"  doc_id: {doc_id}")

    results = []
    print("\nRunning MCP server validations:")
    results.append(test_read_document(doc_id))
    results.append(test_edit_document_insert(service, doc_id))
    results.append(test_edit_document_compound(service, doc_id))
    results.append(test_validate_operations(doc_id))
    results.append(test_error_invalid_address(doc_id))
    results.append(test_error_invalid_operation(doc_id))

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
