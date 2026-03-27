"""Capture write-side input/output pairs for every cataloged operation.

For each operation: snapshot before state, execute mutation, snapshot after state,
save structured test pair to fixtures/mutations/{operation_name}/.

Usage:
    uv run capture_mutations.py                    # Capture all mutations
    uv run capture_mutations.py insert_text_start  # Capture one mutation
"""

import json
import sys
import time
from pathlib import Path

from auth import get_docs_service, get_drive_service

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MUTATIONS_DIR = FIXTURES_DIR / "mutations"


def read_doc(service, doc_id: str) -> dict:
    return service.documents().get(
        documentId=doc_id, includeTabsContent=True
    ).execute()


def get_body(doc: dict) -> list:
    return doc["tabs"][0]["documentTab"]["body"]["content"]


def create_scratch_doc(service, title: str, init_text: str | None = None) -> str:
    """Create a throwaway doc for mutation testing."""
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    if init_text:
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": init_text}}]},
        ).execute()
    return doc_id


def capture(service, doc_id: str, operation_name: str, requests: list, description: str,
            drive_service=None, drive_ops=None):
    """Execute a mutation and save before/request/after/description."""
    out_dir = MUTATIONS_DIR / operation_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Before
    before = read_doc(service, doc_id)
    (out_dir / "before.json").write_text(json.dumps(before, indent=2, ensure_ascii=False))

    # Execute
    if requests:
        service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()
    if drive_ops:
        drive_ops(drive_service, doc_id)
    time.sleep(0.3)

    # After
    after = read_doc(service, doc_id)
    (out_dir / "after.json").write_text(json.dumps(after, indent=2, ensure_ascii=False))

    # Request
    (out_dir / "request.json").write_text(json.dumps(requests, indent=2))

    # Description
    (out_dir / "description.md").write_text(description)

    # Delta summary
    before_body = get_body(before)
    after_body = get_body(after)
    before_end = before_body[-1]["endIndex"] if before_body else 0
    after_end = after_body[-1]["endIndex"] if after_body else 0
    print(f"  {operation_name}: body {before_end} → {after_end} (delta: {after_end - before_end})")


# === Standard test document content ===

STANDARD_DOC = (
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


def build_standard_doc(service) -> str:
    """Create a standard doc with headings and body text for mutation testing."""
    doc_id = create_scratch_doc(service, "arezzo_mutation_test", STANDARD_DOC)

    # Apply heading styles
    text = STANDARD_DOC
    lines = text.split("\n")[:-1]
    offset = 1
    ranges = []
    for line in lines:
        ranges.append((line, offset, offset + len(line) + 1))
        offset += len(line) + 1

    h1 = ["Report Title"]
    h2 = ["Executive Summary", "Revenue Analysis", "Key Metrics", "Conclusion"]

    reqs = []
    for line, start, end in ranges:
        if line in h1:
            reqs.append({"updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_1"}, "fields": "namedStyleType"}})
        elif line in h2:
            reqs.append({"updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"}, "fields": "namedStyleType"}})

    service.documents().batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()
    return doc_id


# === Mutation definitions ===

def run_all(service, drive_service):
    mutations = [
        ("T1_insert_text_start", mut_t1),
        ("T2_insert_text_end", mut_t2),
        ("T3_insert_after_heading", mut_t3),
        ("T4_insert_between_paragraphs", mut_t4),
        ("T5_replace_section", mut_t5),
        ("T6_delete_paragraph", mut_t6),
        ("T7_replace_all_text", mut_t7),
        ("F1_apply_bold", mut_f1),
        ("F2_change_heading_level", mut_f2),
        ("F4_change_font", mut_f4),
        ("F5_add_hyperlink", mut_f5),
        ("S1_insert_table", mut_s1),
        ("S2_add_table_row", mut_s2),
        ("S5_insert_bullet_list", mut_s5),
        ("S6_insert_numbered_list", mut_s6),
        ("S7_convert_to_list", mut_s7),
        ("S8_insert_page_break", mut_s8),
        ("O1_insert_image", mut_o1),
        ("O2_create_header", mut_o2),
        ("O4_insert_footnote", mut_o4),
        ("N1_create_named_range", mut_n1),
        ("N2_replace_named_range_content", mut_n2),
        ("N3_delete_named_range", mut_n3),
    ]

    names = sys.argv[1:] if len(sys.argv) > 1 else [m[0] for m in mutations]
    mut_map = dict(mutations)

    for name in names:
        if name not in mut_map:
            print(f"ERROR: unknown mutation '{name}'")
            sys.exit(1)
        mut_map[name](service, drive_service)
        time.sleep(4)  # rate limit: 60 writes/min, ~4 writes per mutation


def mut_t1(service, drive_service):
    doc_id = build_standard_doc(service)
    capture(service, doc_id, "T1_insert_text_start",
            [{"insertText": {"location": {"index": 1}, "text": "INSERTED AT START.\n"}}],
            "# T1: Insert text at beginning of document\n\n"
            "Inserts a new paragraph at index 1, pushing all existing content forward.\n\n"
            "**Agent intent:** Add a paragraph at the top of the document.\n\n"
            "**Expected shift:** All indices increase by 19 (length of inserted text).")


def mut_t2(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Find last real paragraph (not the trailing empty one)
    last_real_end = body[-2]["endIndex"] if len(body) > 1 else body[-1]["startIndex"]
    capture(service, doc_id, "T2_insert_text_end",
            [{"insertText": {"location": {"index": last_real_end}, "text": "APPENDED AT END.\n"}}],
            "# T2: Insert text at end of document\n\n"
            f"Inserts at index {last_real_end} (before trailing empty paragraph).\n\n"
            "**Agent intent:** Add a paragraph at the end of the document.\n\n"
            "**Expected shift:** Only the trailing empty paragraph shifts.")


def mut_t3(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Find "Revenue Analysis" heading
    target_end = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                if "Revenue Analysis" in run.get("textRun", {}).get("content", ""):
                    target_end = el["endIndex"]
                    break
    capture(service, doc_id, "T3_insert_after_heading",
            [{"insertText": {"location": {"index": target_end}, "text": "Inserted after Revenue Analysis heading.\n"}}],
            "# T3: Insert text after a specific heading\n\n"
            f"Finds 'Revenue Analysis' heading (endIndex={target_end}), inserts after it.\n\n"
            "**Address resolution:** Walk body, match HEADING_2 + text content.\n\n"
            "**Expected shift:** All content after the heading shifts by 41 chars.")


def mut_t4(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Insert between 2nd and 3rd paragraphs (skip sectionBreak)
    paras = [el for el in body if "paragraph" in el]
    insert_idx = paras[2]["endIndex"]  # After the 3rd paragraph (0-indexed)
    capture(service, doc_id, "T4_insert_between_paragraphs",
            [{"insertText": {"location": {"index": insert_idx}, "text": "INSERTED BETWEEN PARAGRAPHS.\n"}}],
            "# T4: Insert text between two paragraphs\n\n"
            f"Inserts at index {insert_idx} (between paragraphs 3 and 4).\n\n"
            "**Agent intent:** Insert a paragraph between existing paragraphs.")


def mut_t5(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Replace content between "Revenue Analysis" and "Key Metrics"
    section_start = section_end = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "Revenue Analysis" in content:
                    section_start = el["endIndex"]
                if "Key Metrics" in content and section_start is not None:
                    section_end = el["startIndex"]
                    break
    capture(service, doc_id, "T5_replace_section",
            [
                {"deleteContentRange": {"range": {"startIndex": section_start, "endIndex": section_end}}},
                {"insertText": {"location": {"index": section_start}, "text": "REPLACEMENT SECTION CONTENT.\n"}},
            ],
            "# T5: Replace text within a section\n\n"
            f"Deletes content from {section_start} to {section_end}, then inserts replacement.\n\n"
            "**Two-step:** delete range + insert at same index = replace.\n\n"
            f"**Net index shift:** {29 - (section_end - section_start)} chars.")


def mut_t6(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Delete the "Total revenue..." paragraph
    target = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                if "Total revenue" in run.get("textRun", {}).get("content", ""):
                    target = el
                    break
    capture(service, doc_id, "T6_delete_paragraph",
            [{"deleteContentRange": {"range": {"startIndex": target["startIndex"], "endIndex": target["endIndex"]}}}],
            "# T6: Delete a paragraph\n\n"
            f"Deletes paragraph at indices {target['startIndex']}-{target['endIndex']}.\n\n"
            f"**Content deleted:** '{target['paragraph']['elements'][0]['textRun']['content'].strip()}'\n\n"
            f"**Expected shift:** All subsequent indices decrease by {target['endIndex'] - target['startIndex']}.")


def mut_t7(service, drive_service):
    doc_id = build_standard_doc(service)
    capture(service, doc_id, "T7_replace_all_text",
            [{"replaceAllText": {
                "containsText": {"text": "revenue", "matchCase": False},
                "replaceText": "REVENUE"
            }}],
            "# T7: Replace all instances of a string\n\n"
            "Replaces 'revenue' → 'REVENUE' (case insensitive).\n\n"
            "**Simplest operation:** No index resolution needed. API handles internally.\n\n"
            "**Note:** Same-length replacement = zero net index shift.")


def mut_f1(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    # Find "15%" and bold it
    body = get_body(doc)
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "15%" in content:
                    offset = run["startIndex"] + content.index("15%")
                    capture(service, doc_id, "F1_apply_bold",
                            [{"updateTextStyle": {
                                "range": {"startIndex": offset, "endIndex": offset + 3},
                                "textStyle": {"bold": True}, "fields": "bold"
                            }}],
                            "# F1: Apply bold to a text range\n\n"
                            f"Bolds '15%' at indices {offset}-{offset + 3}.\n\n"
                            "**Index arithmetic:** None — formatting doesn't change indices.\n\n"
                            "**Key detail:** `fields` mask is critical. Omitting it clears all other styles.")
                    return


def mut_f2(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Change "Key Metrics" from H2 to H3
    for el in body:
        if "paragraph" in el:
            style = el["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "")
            for run in el["paragraph"].get("elements", []):
                if "Key Metrics" in run.get("textRun", {}).get("content", ""):
                    capture(service, doc_id, "F2_change_heading_level",
                            [{"updateParagraphStyle": {
                                "range": {"startIndex": el["startIndex"], "endIndex": el["endIndex"]},
                                "paragraphStyle": {"namedStyleType": "HEADING_3"},
                                "fields": "namedStyleType"
                            }}],
                            "# F2: Change paragraph heading level\n\n"
                            f"Changes 'Key Metrics' from {style} to HEADING_3.\n\n"
                            f"Range: {el['startIndex']}-{el['endIndex']}.\n\n"
                            "**Side effect:** headingId is auto-assigned/updated.")
                    return


def mut_f4(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Change first real paragraph font
    para = [el for el in body if "paragraph" in el][0]
    capture(service, doc_id, "F4_change_font",
            [{"updateTextStyle": {
                "range": {"startIndex": para["startIndex"], "endIndex": para["endIndex"] - 1},
                "textStyle": {
                    "fontSize": {"magnitude": 14, "unit": "PT"},
                    "weightedFontFamily": {"fontFamily": "Georgia", "weight": 400}
                },
                "fields": "fontSize,weightedFontFamily"
            }}],
            "# F4: Change font size and family\n\n"
            f"Sets paragraph at {para['startIndex']}-{para['endIndex']-1} to 14pt Georgia.\n\n"
            "**Note:** Range excludes trailing \\n to avoid affecting the next paragraph's style.")


def mut_f5(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "quarterly" in content.lower():
                    idx = run["startIndex"] + content.lower().index("quarterly")
                    capture(service, doc_id, "F5_add_hyperlink",
                            [{"updateTextStyle": {
                                "range": {"startIndex": idx, "endIndex": idx + 9},
                                "textStyle": {"link": {"url": "https://example.com/q1"}},
                                "fields": "link"
                            }}],
                            "# F5: Add a hyperlink to text\n\n"
                            f"Links 'quarterly' at {idx}-{idx+9} to https://example.com/q1.\n\n"
                            "**Side effect:** Google auto-applies underline + blue foreground color.\n"
                            "The compiler should NOT manually apply these styles.")
                    return


def mut_s1(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Insert table after "Revenue Analysis" section
    target_end = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                if "Total revenue" in run.get("textRun", {}).get("content", ""):
                    target_end = el["endIndex"]
                    break
    # Insert at end of that paragraph (safe: not at segment end)
    capture(service, doc_id, "S1_insert_table",
            [{"insertTable": {"location": {"index": target_end}, "rows": 2, "columns": 3}}],
            "# S1: Insert a table\n\n"
            f"Inserts a 2×3 table at index {target_end}.\n\n"
            "**Index consumption:** Table structural markers + empty cells.\n\n"
            "**Hard edge:** Index must be strictly less than segment endIndex.")


def mut_s2(service, drive_service):
    doc_id = build_standard_doc(service)
    # First insert a table
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    end = body[-1]["endIndex"] - 2
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertTable": {"location": {"index": end}, "rows": 2, "columns": 2}}]}
    ).execute()
    time.sleep(0.3)
    # Now add a row
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    table_el = [el for el in body if "table" in el]
    if table_el:
        table_start = table_el[0]["startIndex"]
        capture(service, doc_id, "S2_add_table_row",
                [{"insertTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": table_start},
                        "rowIndex": 1, "columnIndex": 0
                    }, "insertBelow": True
                }}],
                "# S2: Add a row to an existing table\n\n"
                f"Adds a row below row 1 in table at index {table_start}.\n\n"
                "**Index consumption:** 1 (row marker) + cols × 2 (cell marker + cell \\n).")


def mut_s5(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    end = body[-2]["endIndex"]
    text = "Bullet item one\nBullet item two\nBullet item three\n"
    capture(service, doc_id, "S5_insert_bullet_list",
            [
                {"insertText": {"location": {"index": end}, "text": text}},
                {"createParagraphBullets": {
                    "range": {"startIndex": end, "endIndex": end + len(text)},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                }},
            ],
            "# S5: Insert a bullet list\n\n"
            f"Inserts 3 bullet items at index {end}.\n\n"
            "**Two-step:** Insert text first, then apply bullet formatting.\n\n"
            "**Key insight:** `createParagraphBullets` does NOT change indices.")


def mut_s6(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    end = body[-2]["endIndex"]
    text = "Step one\nStep two\nStep three\n"
    capture(service, doc_id, "S6_insert_numbered_list",
            [
                {"insertText": {"location": {"index": end}, "text": text}},
                {"createParagraphBullets": {
                    "range": {"startIndex": end, "endIndex": end + len(text)},
                    "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN"
                }},
            ],
            "# S6: Insert a numbered list\n\n"
            f"Inserts 3 numbered items at index {end}.\n\n"
            "Same pattern as S5 but with numbered preset.")


def mut_s7(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Convert "Key Metrics" list items to bullets
    start = end = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "Monthly recurring" in content:
                    start = el["startIndex"]
                if "decreased significantly" in content:
                    end = el["endIndex"]
    if start and end:
        capture(service, doc_id, "S7_convert_to_list",
                [{"createParagraphBullets": {
                    "range": {"startIndex": start, "endIndex": end},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
                }}],
                "# S7: Convert existing paragraphs to a bullet list\n\n"
                f"Converts paragraphs at {start}-{end} to bullets.\n\n"
                "**In-place:** No text insertion. Only paragraph property modification.\n\n"
                "**Index arithmetic:** None.")


def mut_s8(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Insert page break before "Conclusion"
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                if "Conclusion" in run.get("textRun", {}).get("content", ""):
                    capture(service, doc_id, "S8_insert_page_break",
                            [{"insertPageBreak": {"location": {"index": el["startIndex"]}}}],
                            "# S8: Insert a page break\n\n"
                            f"Page break at index {el['startIndex']} (before 'Conclusion' heading).\n\n"
                            "**Index consumption:** 2 positions (pageBreak element + trailing textRun).")
                    return


def mut_o1(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Insert image after first heading
    paras = [el for el in body if "paragraph" in el]
    idx = paras[0]["endIndex"]
    capture(service, doc_id, "O1_insert_image",
            [{"insertInlineImage": {
                "location": {"index": idx},
                "uri": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
                "objectSize": {
                    "width": {"magnitude": 150, "unit": "PT"},
                    "height": {"magnitude": 50, "unit": "PT"}
                }
            }}],
            "# O1: Insert an inline image\n\n"
            f"Inserts Google logo image at index {idx}.\n\n"
            "**Index consumption:** Exactly 1 position (inlineObjectElement).\n\n"
            "**Side effect:** Google re-hosts the image. sourceUri != contentUri in the JSON.")


def mut_o2(service, drive_service):
    doc_id = build_standard_doc(service)
    capture(service, doc_id, "O2_create_header",
            [
                {"createHeader": {"type": "DEFAULT"}},
                {"createFooter": {"type": "DEFAULT"}},
            ],
            "# O2: Create header and footer\n\n"
            "Creates default header and footer segments.\n\n"
            "**Index arithmetic:** None in body. New segments have own index spaces.\n\n"
            "**Side effect:** documentStyle gets defaultHeaderId/defaultFooterId.")


def mut_o4(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Insert footnote after "15%"
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "15%" in content:
                    idx = run["startIndex"] + content.index("15%") + 3
                    capture(service, doc_id, "O4_insert_footnote",
                            [{"createFootnote": {"location": {"index": idx}}}],
                            "# O4: Insert a footnote\n\n"
                            f"Inserts footnote reference at index {idx} (after '15%').\n\n"
                            "**Index consumption:** 1 position in body (footnoteReference element).\n\n"
                            "**Side effect:** New footnote segment created in documentTab.footnotes.")
                    return


def mut_n1(service, drive_service):
    doc_id = build_standard_doc(service)
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Create named range around the Executive Summary section
    section_start = section_end = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "Executive Summary" in content:
                    section_start = el["startIndex"]
                if "Revenue Analysis" in content and section_start is not None:
                    section_end = el["startIndex"]
                    break
    if section_start and section_end:
        capture(service, doc_id, "N1_create_named_range",
                [{"createNamedRange": {
                    "name": "executive_summary",
                    "range": {"startIndex": section_start, "endIndex": section_end}
                }}],
                "# N1: Create a named range\n\n"
                f"Named range 'executive_summary' spans {section_start}-{section_end}.\n\n"
                "**Index arithmetic:** None — named ranges are metadata.\n\n"
                "**Key detail:** Range stored in documentTab.namedRanges, not in body content.")


def mut_n2(service, drive_service):
    doc_id = build_standard_doc(service)
    # First create a named range
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    section_start = section_end = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                content = run.get("textRun", {}).get("content", "")
                if "Executive Summary" in content:
                    section_start = el["endIndex"]  # After the heading itself
                if "Revenue Analysis" in content and section_start is not None:
                    section_end = el["startIndex"]
                    break
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"createNamedRange": {
            "name": "exec_summary_body",
            "range": {"startIndex": section_start, "endIndex": section_end}
        }}]}
    ).execute()
    time.sleep(0.3)

    # Now replace the content within the named range
    doc = read_doc(service, doc_id)
    nr = doc["tabs"][0]["documentTab"].get("namedRanges", {})
    range_data = nr.get("exec_summary_body", {}).get("namedRanges", [{}])[0]
    r = range_data.get("ranges", [{}])[0]
    capture(service, doc_id, "N2_replace_named_range_content",
            [
                {"deleteContentRange": {"range": {"startIndex": r["startIndex"], "endIndex": r["endIndex"]}}},
                {"insertText": {"location": {"index": r["startIndex"]},
                                "text": "REPLACED NAMED RANGE CONTENT.\n"}},
            ],
            "# N2: Replace content within a named range\n\n"
            f"Reads named range 'exec_summary_body' ({r['startIndex']}-{r['endIndex']}), "
            "deletes content, inserts replacement.\n\n"
            "**Caution:** Named range indices become stale after this operation.\n"
            "The range must be re-created if needed again.")


def mut_n3(service, drive_service):
    doc_id = build_standard_doc(service)
    # Create a named range first
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"createNamedRange": {
            "name": "temp_range",
            "range": {"startIndex": 1, "endIndex": 14}
        }}]}
    ).execute()
    time.sleep(0.3)
    doc = read_doc(service, doc_id)
    nr = doc["tabs"][0]["documentTab"].get("namedRanges", {})
    nr_id = nr.get("temp_range", {}).get("namedRanges", [{}])[0].get("namedRangeId", "")
    capture(service, doc_id, "N3_delete_named_range",
            [{"deleteNamedRange": {"namedRangeId": nr_id}}],
            "# N3: Delete a named range\n\n"
            f"Deletes named range 'temp_range' (ID: {nr_id}).\n\n"
            "**Index arithmetic:** None — metadata-only operation.\n\n"
            "**Note:** Can also delete by name instead of ID.")


def main():
    docs_service = get_docs_service()
    drive_service = get_drive_service()
    MUTATIONS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Capturing mutations to {MUTATIONS_DIR}/")
    run_all(docs_service, drive_service)
    print("\nDone.")


if __name__ == "__main__":
    main()
