"""Phase 3: Live API validation — compile operations and execute against real Google Docs.

For each test case:
1. Create a scratch document with known content
2. Compile operations using the Arezzo compiler
3. Execute the compiled batchUpdate against the real API
4. Read the document back and verify the expected mutation occurred

Usage:
    uv run validate_live.py              # Run all validations
    uv run validate_live.py insert_text  # Run one validation
"""

import json
import sys
import time
from pathlib import Path

from auth import get_docs_service
from arezzo.compiler import compile_operations
from arezzo.parser import parse_document

RESULTS_DIR = Path(__file__).parent / "fixtures" / "validation"


def create_standard_doc(service) -> tuple[str, dict]:
    """Create a standard test doc and return (doc_id, full_doc_json)."""
    text = (
        "Report Title\n"
        "Executive Summary\n"
        "This report covers quarterly performance metrics and key findings.\n"
        "Revenue Analysis\n"
        "Total revenue increased by 15% compared to the previous quarter.\n"
        "Key Metrics\n"
        "Monthly recurring revenue reached a new high.\n"
        "Customer acquisition cost decreased significantly.\n"
        "Conclusion\n"
        "The outlook for next quarter remains positive.\n"
    )
    doc = service.documents().create(body={"title": "arezzo_validation_test"}).execute()
    doc_id = doc["documentId"]

    # Insert text
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
    ).execute()

    # Apply headings
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

    # Read back full document
    full_doc = service.documents().get(
        documentId=doc_id, includeTabsContent=True
    ).execute()
    return doc_id, full_doc


def read_doc(service, doc_id: str) -> dict:
    return service.documents().get(
        documentId=doc_id, includeTabsContent=True
    ).execute()


def get_body_text(doc: dict) -> str:
    """Extract all body text from a document."""
    body = doc["tabs"][0]["documentTab"]["body"]["content"]
    parts = []
    for el in body:
        if "paragraph" in el:
            for elem in el["paragraph"].get("elements", []):
                tr = elem.get("textRun")
                if tr:
                    parts.append(tr.get("content", ""))
    return "".join(parts)


def validate_and_report(
    name: str, service, doc_id: str, full_doc: dict,
    operations: list[dict], check_fn
):
    """Compile, execute, verify, report."""
    out_dir = RESULTS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Compile
    result = compile_operations(full_doc, operations)
    (out_dir / "compiled_request.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False)
    )

    # Execute
    try:
        service.documents().batchUpdate(
            documentId=doc_id, body=result
        ).execute()
    except Exception as e:
        print(f"  {name}: FAIL — batchUpdate error: {e}")
        (out_dir / "result.txt").write_text(f"FAIL: {e}")
        return False

    time.sleep(0.3)

    # Read back
    after = read_doc(service, doc_id)
    (out_dir / "after.json").write_text(
        json.dumps(after, indent=2, ensure_ascii=False)
    )

    # Verify
    try:
        check_fn(after)
        print(f"  {name}: PASS")
        (out_dir / "result.txt").write_text("PASS")
        return True
    except AssertionError as e:
        print(f"  {name}: FAIL — {e}")
        (out_dir / "result.txt").write_text(f"FAIL: {e}")
        return False


# === Validation cases ===

def val_insert_text_after_heading(service):
    doc_id, full_doc = create_standard_doc(service)
    ops = [{
        "type": "insert_text",
        "address": {"heading": "Revenue Analysis"},
        "params": {"text": "AREZZO INSERTED THIS PARAGRAPH.\n"},
    }]

    def check(after):
        text = get_body_text(after)
        assert "AREZZO INSERTED THIS PARAGRAPH." in text
        # Should appear after "Revenue Analysis" heading
        ra_idx = text.index("Revenue Analysis")
        ins_idx = text.index("AREZZO INSERTED THIS PARAGRAPH.")
        assert ins_idx > ra_idx

    return validate_and_report("insert_text_after_heading", service, doc_id, full_doc, ops, check)


def val_replace_all_text(service):
    doc_id, full_doc = create_standard_doc(service)
    ops = [{
        "type": "replace_all_text",
        "params": {"find_text": "revenue", "replace_text": "REVENUE", "match_case": False},
    }]

    def check(after):
        text = get_body_text(after)
        # All instances of "revenue" (case-insensitive) should now be "REVENUE"
        assert "REVENUE" in text
        # No lowercase "revenue" should remain
        for word in text.split():
            if word.strip(".,;:!?()").lower() == "revenue":
                assert word.strip(".,;:!?()") == "REVENUE", f"Found unreplaced: {word}"

    return validate_and_report("replace_all_text", service, doc_id, full_doc, ops, check)


def val_apply_bold_and_insert(service):
    """Mixed content + format operation."""
    doc_id, full_doc = create_standard_doc(service)
    parsed = parse_document(full_doc)

    # Find "15%" in body
    target_idx = None
    for el in parsed.body:
        if "paragraph" in el:
            for elem in el["paragraph"].get("elements", []):
                tr = elem.get("textRun", {})
                if "15%" in tr.get("content", ""):
                    content = tr["content"]
                    target_idx = elem["startIndex"] + content.index("15%")
                    break

    ops = [
        {"type": "insert_text", "address": {"end": True},
         "params": {"text": "AREZZO APPENDED.\n"}},
        {"type": "update_text_style",
         "address": {"index": target_idx},
         "params": {"text_style": {"bold": True}, "fields": "bold", "length": 3}},
    ]

    def check(after):
        text = get_body_text(after)
        assert "AREZZO APPENDED." in text
        # Verify bold was applied (check element styles)
        body = after["tabs"][0]["documentTab"]["body"]["content"]
        for el in body:
            if "paragraph" in el:
                for elem in el["paragraph"].get("elements", []):
                    tr = elem.get("textRun", {})
                    if "15%" in tr.get("content", ""):
                        assert tr.get("textStyle", {}).get("bold") is True, "15% should be bold"
                        return
        raise AssertionError("Could not find 15% in output")

    return validate_and_report("apply_bold_and_insert", service, doc_id, full_doc, ops, check)


def val_insert_table(service):
    doc_id, full_doc = create_standard_doc(service)
    parsed = parse_document(full_doc)

    # Insert table after "Revenue Analysis" heading
    entries = parsed.heading_index.get("Revenue Analysis")
    idx = entries[0][1]  # endIndex of heading

    ops = [{
        "type": "insert_table",
        "address": {"index": idx},
        "params": {"rows": 2, "columns": 3},
    }]

    def check(after):
        body = after["tabs"][0]["documentTab"]["body"]["content"]
        tables = [el for el in body if "table" in el]
        assert len(tables) >= 1, "Should have at least one table"
        t = tables[0]["table"]
        assert t["rows"] == 2
        assert t["columns"] == 3

    return validate_and_report("insert_table", service, doc_id, full_doc, ops, check)


def val_create_named_range(service):
    doc_id, full_doc = create_standard_doc(service)
    parsed = parse_document(full_doc)

    ops = [{
        "type": "create_named_range",
        "address": {"heading": "Executive Summary"},
        "params": {"name": "arezzo_test_range"},
    }]

    def check(after):
        doc_tab = after["tabs"][0]["documentTab"]
        nr = doc_tab.get("namedRanges", {})
        assert "arezzo_test_range" in nr, f"Named range not found. Available: {list(nr.keys())}"

    return validate_and_report("create_named_range", service, doc_id, full_doc, ops, check)


def val_insert_bullet_list(service):
    doc_id, full_doc = create_standard_doc(service)

    ops = [{
        "type": "insert_bullet_list",
        "address": {"end": True},
        "params": {"items": ["First item", "Second item", "Third item"]},
    }]

    def check(after):
        body = after["tabs"][0]["documentTab"]["body"]["content"]
        bullets = [el for el in body if "paragraph" in el and "bullet" in el["paragraph"]]
        assert len(bullets) >= 3, f"Expected 3+ bullet paragraphs, got {len(bullets)}"

    return validate_and_report("insert_bullet_list", service, doc_id, full_doc, ops, check)


def val_create_header_footer(service):
    doc_id, full_doc = create_standard_doc(service)

    ops = [
        {"type": "create_header", "params": {}},
        {"type": "create_footer", "params": {}},
    ]

    def check(after):
        doc_tab = after["tabs"][0]["documentTab"]
        assert len(doc_tab.get("headers", {})) > 0, "No headers created"
        assert len(doc_tab.get("footers", {})) > 0, "No footers created"

    return validate_and_report("create_header_footer", service, doc_id, full_doc, ops, check)


def val_insert_page_break(service):
    doc_id, full_doc = create_standard_doc(service)
    parsed = parse_document(full_doc)

    # Insert page break before "Conclusion"
    entries = parsed.heading_index.get("Conclusion")
    idx = entries[0][0]  # startIndex of heading

    ops = [{
        "type": "insert_page_break",
        "address": {"index": idx},
    }]

    def check(after):
        body = after["tabs"][0]["documentTab"]["body"]["content"]
        page_breaks = []
        for el in body:
            if "paragraph" in el:
                for elem in el["paragraph"].get("elements", []):
                    if "pageBreak" in elem:
                        page_breaks.append(elem)
        assert len(page_breaks) >= 1, "No page break found"

    return validate_and_report("insert_page_break", service, doc_id, full_doc, ops, check)


VALIDATIONS = {
    "insert_text": val_insert_text_after_heading,
    "replace_all": val_replace_all_text,
    "bold_and_insert": val_apply_bold_and_insert,
    "insert_table": val_insert_table,
    "named_range": val_create_named_range,
    "bullet_list": val_insert_bullet_list,
    "header_footer": val_create_header_footer,
    "page_break": val_insert_page_break,
}


def main():
    service = get_docs_service()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    names = sys.argv[1:] if len(sys.argv) > 1 else list(VALIDATIONS.keys())
    passed = 0
    failed = 0

    print(f"Running {len(names)} live validations...")
    for name in names:
        if name not in VALIDATIONS:
            print(f"  ERROR: unknown validation '{name}'")
            sys.exit(1)
        ok = VALIDATIONS[name](service)
        if ok:
            passed += 1
        else:
            failed += 1
        time.sleep(4)  # rate limit: 60 writes/min

    print(f"\n{passed} passed, {failed} failed out of {passed + failed} total.")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
