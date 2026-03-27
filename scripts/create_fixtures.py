"""Create Google Docs test fixtures for the complexity ladder.

Creates each fixture doc via the Docs API, populates it with structural
content, and writes doc IDs to fixtures/manifest.json.

Usage:
    uv run create_fixtures.py                    # Create all fixtures
    uv run create_fixtures.py 01_plain_text      # Create one fixture
"""

import json
import sys
import time
from pathlib import Path

from auth import get_docs_service, get_drive_service

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_FILE = FIXTURES_DIR / "manifest.json"


def load_manifest() -> dict:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text())
    return {}


def save_manifest(manifest: dict):
    FIXTURES_DIR.mkdir(exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))


def create_doc(service, title: str, requests: list | None = None) -> str:
    """Create a doc and optionally apply batchUpdate requests."""
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    if requests:
        service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()
    return doc_id


def batch(service, doc_id: str, requests: list):
    """Execute a batchUpdate."""
    service.documents().batchUpdate(
        documentId=doc_id, body={"requests": requests}
    ).execute()


def read_doc(service, doc_id: str) -> dict:
    """Read the full document including tabs content."""
    return service.documents().get(
        documentId=doc_id, includeTabsContent=True
    ).execute()


def get_body(doc: dict) -> list:
    """Get body content elements from the first tab."""
    return doc["tabs"][0]["documentTab"]["body"]["content"]


def line_ranges(text: str, base: int = 1) -> list[tuple[str, int, int]]:
    """Split text into lines and return (line_text, start_index, end_index) tuples."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    result = []
    offset = base
    for line in lines:
        start = offset
        end = offset + len(line) + 1  # include \n
        result.append((line, start, end))
        offset = end
    return result


# ============================================================
# Fixture builders — each returns batchUpdate requests.
# The doc starts with a single empty paragraph at index 1.
# ============================================================


def build_01_plain_text() -> list:
    text = (
        "This is the first paragraph of plain text. It contains no formatting, "
        "no headings, and no structural elements. Just simple text content.\n"
        "This is the second paragraph. It demonstrates that the document contains "
        "multiple distinct paragraphs separated by newline characters.\n"
        "The third paragraph is here. Each paragraph is a separate structural "
        "element in the Google Docs JSON representation.\n"
        "Fourth and final paragraph. This fixture exercises the simplest possible "
        "document structure — body content with plain text only.\n"
    )
    return [{"insertText": {"location": {"index": 1}, "text": text}}]


def build_02_heading_hierarchy() -> list:
    text = (
        "Document Title\n"
        "This is body text under the document title heading.\n"
        "Section One\n"
        "Body text under section one. This paragraph sits between H2 headings.\n"
        "Subsection A\n"
        "Body text under subsection A. This is the deepest heading level tested.\n"
        "Subsection B\n"
        "Body text under subsection B.\n"
        "Section Two\n"
        "Body text under section two.\n"
    )
    requests = [{"insertText": {"location": {"index": 1}, "text": text}}]

    headings = {
        "HEADING_1": ["Document Title"],
        "HEADING_2": ["Section One", "Section Two"],
        "HEADING_3": ["Subsection A", "Subsection B"],
    }
    ranges = line_ranges(text)
    for style, titles in headings.items():
        for line_text, start, end in ranges:
            if line_text in titles:
                requests.append({
                    "updateParagraphStyle": {
                        "range": {"startIndex": start, "endIndex": end},
                        "paragraphStyle": {"namedStyleType": style},
                        "fields": "namedStyleType",
                    }
                })
    return requests


def build_03_inline_formatting() -> list:
    text = (
        "This paragraph has bold text and italic text and underlined text "
        "and a hyperlink and mixed bold-italic text within a single paragraph.\n"
        "This second paragraph has no formatting for comparison.\n"
    )
    requests = [{"insertText": {"location": {"index": 1}, "text": text}}]

    formats = [
        ("bold text", {"bold": True}, "bold"),
        ("italic text", {"italic": True}, "italic"),
        ("underlined text", {"underline": True}, "underline"),
        ("a hyperlink", {"link": {"url": "https://example.com"}}, "link"),
        ("mixed bold-italic text", {"bold": True, "italic": True}, "bold,italic"),
    ]
    for target, style, fields in formats:
        idx = 1 + text.index(target)
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(target)},
                "textStyle": style,
                "fields": fields,
            }
        })
    return requests


def build_04_lists() -> list:
    text = (
        "Bullet list items:\n"
        "First bullet item\n"
        "Second bullet item\n"
        "Third bullet item\n"
        "Numbered list items:\n"
        "First numbered item\n"
        "Second numbered item\n"
        "Third numbered item\n"
        "Nested list items:\n"
        "Top level item one\n"
        "Nested under item one\n"
        "Deeper nested item\n"
        "Top level item two\n"
        "Nested under item two\n"
    )
    requests = [{"insertText": {"location": {"index": 1}, "text": text}}]
    ranges = line_ranges(text)

    bullet_indices = [1, 2, 3]
    numbered_indices = [5, 6, 7]
    nested_all = [9, 10, 11, 12, 13]
    nest_level1 = [10, 13]
    nest_level2 = [11]

    for i in bullet_indices:
        _, s, e = ranges[i]
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": s, "endIndex": e},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })
    for i in numbered_indices:
        _, s, e = ranges[i]
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": s, "endIndex": e},
                "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN",
            }
        })
    for i in nested_all:
        _, s, e = ranges[i]
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": s, "endIndex": e},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })
    for i in nest_level1:
        _, s, e = ranges[i]
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": s, "endIndex": e},
                "paragraphStyle": {"indentStart": {"magnitude": 36, "unit": "PT"}},
                "fields": "indentStart",
            }
        })
    for i in nest_level2:
        _, s, e = ranges[i]
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": s, "endIndex": e},
                "paragraphStyle": {"indentStart": {"magnitude": 72, "unit": "PT"}},
                "fields": "indentStart",
            }
        })
    return requests


def build_05_tables() -> list:
    """Create doc with title. Table inserted in post_create after reading doc."""
    return [
        {"insertText": {"location": {"index": 1}, "text": "Simple 3x3 Table\n"}},
    ]


def post_05_tables(service, doc_id: str):
    """Insert tables and fill cells."""
    # Insert 3x3 table after the title paragraph
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    # Insert table at end of last paragraph (before its trailing \n)
    end = body[-1]["endIndex"] - 1
    batch(service, doc_id, [
        {"insertTable": {"location": {"index": end}, "rows": 3, "columns": 3}},
    ])

    doc = read_doc(service, doc_id)
    body = get_body(doc)
    tables = [el for el in body if "table" in el]
    if not tables:
        print("    WARNING: no table found")
        return

    # Fill 3x3 cells in reverse order to avoid index shifting
    table = tables[0]["table"]
    requests = []
    for r_idx, row in enumerate(table["tableRows"]):
        for c_idx, cell in enumerate(row["tableCells"]):
            idx = cell["content"][0]["startIndex"]
            requests.append({
                "insertText": {
                    "location": {"index": idx},
                    "text": f"R{r_idx+1}C{c_idx+1}",
                }
            })
    requests.reverse()
    batch(service, doc_id, requests)

    # Add second table
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    end = body[-1]["endIndex"] - 1
    batch(service, doc_id, [
        {"insertText": {"location": {"index": end}, "text": "\nSmall 2x2 Table\n"}},
    ])
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    end = body[-1]["endIndex"] - 1
    batch(service, doc_id, [
        {"insertTable": {"location": {"index": end}, "rows": 2, "columns": 2}},
    ])

    # Fill 2x2 cells
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    tables = [el for el in body if "table" in el]
    if len(tables) >= 2:
        table2 = tables[1]["table"]
        requests = []
        for r_idx, row in enumerate(table2["tableRows"]):
            for c_idx, cell in enumerate(row["tableCells"]):
                idx = cell["content"][0]["startIndex"]
                requests.append({
                    "insertText": {
                        "location": {"index": idx},
                        "text": f"T2R{r_idx+1}C{c_idx+1}",
                    }
                })
        requests.reverse()
        batch(service, doc_id, requests)


def build_06_images() -> list:
    # Use a Google-hosted image that is reliably available
    return [
        {"insertText": {"location": {"index": 1}, "text": "Document with an inline image below:\n"}},
        {"insertInlineImage": {
            "location": {"index": 1 + len("Document with an inline image below:\n")},
            "uri": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
            "objectSize": {
                "width": {"magnitude": 200, "unit": "PT"},
                "height": {"magnitude": 68, "unit": "PT"},
            },
        }},
    ]


def build_07_headers_footers_footnotes() -> list:
    text = (
        "Document with headers, footers, and footnotes.\n"
        "This paragraph contains a footnote reference right here at the end.\n"
        "This is a normal paragraph after the footnote paragraph.\n"
    )
    line1 = "Document with headers, footers, and footnotes.\n"
    line2 = "This paragraph contains a footnote reference right here at the end.\n"
    fn_idx = 1 + len(line1) + len(line2) - 2  # before the period on line 2

    return [
        {"insertText": {"location": {"index": 1}, "text": text}},
        {"createHeader": {"type": "DEFAULT"}},
        {"createFooter": {"type": "DEFAULT"}},
        {"createFootnote": {"location": {"index": fn_idx}}},
    ]


def post_07_headers_footers(service, doc_id: str):
    """Fill header, footer, and footnote content."""
    doc = read_doc(service, doc_id)
    doc_tab = doc["tabs"][0]["documentTab"]
    requests = []

    for hid, header in doc_tab.get("headers", {}).items():
        idx = header["content"][0].get("startIndex", 0)
        requests.append({
            "insertText": {
                "location": {"segmentId": hid, "index": idx},
                "text": "Arezzo Test Fixture — Header",
            }
        })
    for fid, footer in doc_tab.get("footers", {}).items():
        idx = footer["content"][0].get("startIndex", 0)
        requests.append({
            "insertText": {
                "location": {"segmentId": fid, "index": idx},
                "text": "Page footer content",
            }
        })
    for fnid, fn in doc_tab.get("footnotes", {}).items():
        idx = fn["content"][0].get("startIndex", 0)
        requests.append({
            "insertText": {
                "location": {"segmentId": fnid, "index": idx},
                "text": "This is the footnote content explaining the referenced statement.",
            }
        })
    if requests:
        batch(service, doc_id, requests)


def build_08_named_ranges() -> list:
    text = (
        "Introduction Section\n"
        "This is the introduction. It provides context and background.\n"
        "Conclusion Section\n"
        "This is the conclusion. It summarizes the key points.\n"
    )
    intro_end = 1 + len("Introduction Section\n") + len(
        "This is the introduction. It provides context and background.\n"
    )
    conclusion_end = intro_end + len("Conclusion Section\n") + len(
        "This is the conclusion. It summarizes the key points.\n"
    )
    return [
        {"insertText": {"location": {"index": 1}, "text": text}},
        {"createNamedRange": {
            "name": "introduction_section",
            "range": {"startIndex": 1, "endIndex": intro_end},
        }},
        {"createNamedRange": {
            "name": "conclusion_section",
            "range": {"startIndex": intro_end, "endIndex": conclusion_end},
        }},
    ]


def build_09_tabs() -> list:
    """Placeholder — tabs may not be creatable via batchUpdate."""
    text = (
        "Tab 1 Content\n"
        "This is the default first tab. Additional tabs may need manual creation "
        "if the Docs API does not support tab creation via batchUpdate.\n"
    )
    return [{"insertText": {"location": {"index": 1}, "text": text}}]


def post_09_tabs(service, doc_id: str):
    """Attempt to create additional tabs. Log if API doesn't support it."""
    try:
        batch(service, doc_id, [
            {"addTab": {"tabProperties": {"title": "Second Tab"}}},
        ])
        # If that worked, add content to the second tab
        doc = read_doc(service, doc_id)
        tabs = doc.get("tabs", [])
        if len(tabs) >= 2:
            tab_id = tabs[1]["tabProperties"]["tabId"]
            batch(service, doc_id, [{
                "insertText": {
                    "location": {"index": 1, "tabId": tab_id},
                    "text": "Second tab content. This tab was created programmatically.\n",
                }
            }])
            # Add a third tab
            batch(service, doc_id, [
                {"addTab": {"tabProperties": {"title": "Third Tab"}}},
            ])
            doc = read_doc(service, doc_id)
            tabs = doc.get("tabs", [])
            if len(tabs) >= 3:
                tab_id = tabs[2]["tabProperties"]["tabId"]
                batch(service, doc_id, [{
                    "insertText": {
                        "location": {"index": 1, "tabId": tab_id},
                        "text": "Third tab content with different structure.\nSecond paragraph in third tab.\n",
                    }
                }])
        print("    tabs: created programmatically")
    except Exception as e:
        print(f"    tabs: API does not support tab creation ({e})")
        print("    tabs: Will needs to add tabs manually via the Docs UI")


def build_10_comments() -> list:
    """Body text. Comments added via Drive API in post_create."""
    text = (
        "This paragraph will have a comment attached to it.\n"
        "This paragraph will have a comment with a reply thread.\n"
        "This paragraph has no comments for comparison.\n"
    )
    return [{"insertText": {"location": {"index": 1}, "text": text}}]


def post_10_comments_drive(drive_service, doc_id: str):
    """Add comments via Drive API."""
    # Comment 1
    drive_service.comments().create(
        fileId=doc_id,
        body={
            "content": "Review comment on the first paragraph.",
            "quotedFileContent": {
                "mimeType": "text/html",
                "value": "This paragraph will have a comment attached to it.",
            },
        },
        fields="id",
    ).execute()
    time.sleep(0.5)

    # Comment 2 with reply
    c2 = drive_service.comments().create(
        fileId=doc_id,
        body={
            "content": "This paragraph needs revision.",
            "quotedFileContent": {
                "mimeType": "text/html",
                "value": "This paragraph will have a comment with a reply thread.",
            },
        },
        fields="id",
    ).execute()
    time.sleep(0.5)

    drive_service.replies().create(
        fileId=doc_id,
        commentId=c2["id"],
        body={"content": "Agreed, updating now."},
        fields="id",
    ).execute()


def build_11_kitchen_sink() -> list:
    text = (
        "Quarterly Business Review\n"
        "Executive Summary\n"
        "This report covers Q1 performance metrics. "
        "Key findings include strong revenue growth and improved customer retention.\n"
        "Revenue Analysis\n"
        "Total revenue increased by 15% compared to the previous quarter. "
        "Primary drivers were enterprise contracts and upsells.\n"
        "Key Metrics\n"
        "Monthly recurring revenue reached a new high\n"
        "Customer acquisition cost decreased by 8%\n"
        "Net promoter score improved to 72\n"
        "Department Updates\n"
        "Engineering completed 3 major releases. Sales closed 12 enterprise deals. "
        "Marketing launched the new brand campaign.\n"
        "Next Steps\n"
        "Focus areas for Q2 include international expansion and platform stability.\n"
    )
    requests = [{"insertText": {"location": {"index": 1}, "text": text}}]
    ranges = line_ranges(text)
    range_map = {r[0]: (r[1], r[2]) for r in ranges}

    h1 = ["Quarterly Business Review"]
    h2 = ["Executive Summary", "Revenue Analysis", "Department Updates", "Next Steps"]
    h3 = ["Key Metrics"]

    for style, titles in [("HEADING_1", h1), ("HEADING_2", h2), ("HEADING_3", h3)]:
        for title in titles:
            s, e = range_map[title]
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": s, "endIndex": e},
                    "paragraphStyle": {"namedStyleType": style},
                    "fields": "namedStyleType",
                }
            })

    # Bullet list
    for title in [
        "Monthly recurring revenue reached a new high",
        "Customer acquisition cost decreased by 8%",
        "Net promoter score improved to 72",
    ]:
        s, e = range_map[title]
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": s, "endIndex": e},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })

    # Bold key numbers
    for target in ["15%", "8%", "72"]:
        idx = 1 + text.index(target)
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": idx, "endIndex": idx + len(target)},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        })

    # Italic "Key findings"
    idx = 1 + text.index("Key findings")
    requests.append({
        "updateTextStyle": {
            "range": {"startIndex": idx, "endIndex": idx + len("Key findings")},
            "textStyle": {"italic": True},
            "fields": "italic",
        }
    })

    return requests


def post_11_kitchen_sink(service, doc_id: str):
    """Add table and footnote to kitchen_sink after initial content."""
    # Insert a revenue table before "Key Metrics" heading
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    target_idx = None
    for el in body:
        if "paragraph" in el:
            for run in el["paragraph"].get("elements", []):
                if "Key Metrics" in run.get("textRun", {}).get("content", ""):
                    target_idx = el["startIndex"]
                    break
    if target_idx:
        batch(service, doc_id, [
            {"insertText": {"location": {"index": target_idx}, "text": "Revenue by Region\n"}},
        ])
        doc = read_doc(service, doc_id)
        body = get_body(doc)
        table_idx = None
        for el in body:
            if "paragraph" in el:
                for run in el["paragraph"].get("elements", []):
                    if "Revenue by Region" in run.get("textRun", {}).get("content", ""):
                        table_idx = el["endIndex"] - 1
                        break
        if table_idx:
            batch(service, doc_id, [
                {"insertTable": {"location": {"index": table_idx}, "rows": 3, "columns": 2}},
            ])

    # Footnote on "customer retention"
    doc = read_doc(service, doc_id)
    body = get_body(doc)
    for el in body:
        if "paragraph" not in el:
            continue
        for run in el["paragraph"].get("elements", []):
            content = run.get("textRun", {}).get("content", "")
            if "customer retention" in content:
                fn_idx = run["startIndex"] + content.index("customer retention") + len("customer retention")
                batch(service, doc_id, [
                    {"createFootnote": {"location": {"index": fn_idx}}},
                ])
                doc2 = read_doc(service, doc_id)
                footnotes = doc2["tabs"][0]["documentTab"].get("footnotes", {})
                for fnid, fn in footnotes.items():
                    batch(service, doc_id, [{
                        "insertText": {
                            "location": {"segmentId": fnid, "index": fn["content"][0].get("startIndex", 0)},
                            "text": "Retention measured as 12-month rolling average.",
                        }
                    }])
                return


def build_12_horizontal_rules_page_breaks() -> list:
    """Additional rung: horizontal rules and page breaks."""
    text = (
        "Text before the horizontal rule.\n"
        "Text after the horizontal rule, before the page break.\n"
        "Text after the page break on the new page.\n"
    )
    line1 = "Text before the horizontal rule.\n"
    line2 = "Text after the horizontal rule, before the page break.\n"
    hr_idx = 1 + len(line1)
    pb_idx = hr_idx + len(line2)
    return [
        {"insertText": {"location": {"index": 1}, "text": text}},
        {"insertPageBreak": {"location": {"index": pb_idx}}},
        # Horizontal rule goes between line 1 and line 2
        # insertPageBreak shifts indices, so HR must be inserted before PB text
        # Actually, we insert text first, then PB, then HR.
        # PB inserted at pb_idx shifts everything after by 2 (PB element).
        # HR should be inserted at hr_idx — but PB was after that, so hr_idx is stable.
    ]


def post_12_hr_pb(service, doc_id: str):
    """Insert horizontal rule (not available as batchUpdate request — use workaround)."""
    # The Docs API doesn't have a direct insertHorizontalRule request.
    # Horizontal rules appear as paragraph elements with a horizontalRule field.
    # They can be observed in existing docs but creation may require a different approach.
    # For now, we have the page break. Note the HR limitation in findings.
    pass


def build_13_bookmarks() -> list:
    """Additional rung: bookmarks. API does NOT support createBookmark — UI only."""
    text = (
        "Section with a bookmark target here.\n"
        "More content between the bookmarks.\n"
        "Another bookmark target in this section.\n"
    )
    return [{"insertText": {"location": {"index": 1}, "text": text}}]


# ============================================================
# Registry
# ============================================================

FIXTURES = {
    "01_plain_text": {"build": build_01_plain_text},
    "02_heading_hierarchy": {"build": build_02_heading_hierarchy},
    "03_inline_formatting": {"build": build_03_inline_formatting},
    "04_lists": {"build": build_04_lists},
    "05_tables": {"build": build_05_tables, "post": post_05_tables},
    "06_images": {"build": build_06_images},
    "07_headers_footers_footnotes": {
        "build": build_07_headers_footers_footnotes,
        "post": post_07_headers_footers,
    },
    "08_named_ranges": {"build": build_08_named_ranges},
    "09_tabs": {"build": build_09_tabs, "post": post_09_tabs},
    "10_comments": {
        "build": build_10_comments,
        "post_drive": post_10_comments_drive,
    },
    "11_kitchen_sink": {"build": build_11_kitchen_sink, "post": post_11_kitchen_sink},
    "12_horizontal_rules_page_breaks": {
        "build": build_12_horizontal_rules_page_breaks,
        "post": post_12_hr_pb,
    },
    "13_bookmarks": {"build": build_13_bookmarks},
}


def main():
    docs_service = get_docs_service()
    drive_service = get_drive_service()
    manifest = load_manifest()

    names = sys.argv[1:] if len(sys.argv) > 1 else list(FIXTURES.keys())
    created = 0

    for name in names:
        if name not in FIXTURES:
            print(f"ERROR: unknown fixture '{name}'")
            sys.exit(1)

        if name in manifest:
            print(f"  {name}: exists ({manifest[name][:12]}...), skipping")
            continue

        spec = FIXTURES[name]
        title = f"arezzo_fixture_{name}"
        print(f"  {name}: creating...")

        requests = spec["build"]()
        doc_id = create_doc(docs_service, title, requests)

        if "post" in spec:
            spec["post"](docs_service, doc_id)
        if "post_drive" in spec:
            spec["post_drive"](drive_service, doc_id)

        manifest[name] = doc_id
        save_manifest(manifest)
        print(f"  {name}: done → {doc_id}")
        created += 1
        time.sleep(0.3)  # gentle rate limiting

    print(f"\n{created} created, {len(manifest)} total in manifest.")
    print(f"Manifest: {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
