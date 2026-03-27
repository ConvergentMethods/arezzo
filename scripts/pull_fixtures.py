"""Pull Google Docs JSON fixtures via documents.get.

Usage:
    uv run pull_fixtures.py              # Pull all fixtures in manifest
    uv run pull_fixtures.py plain_text   # Pull a single fixture by name
"""

import json
import sys
from pathlib import Path

from auth import get_docs_service

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_FILE = FIXTURES_DIR / "manifest.json"


def load_manifest() -> dict:
    if not MANIFEST_FILE.exists():
        print(f"ERROR: {MANIFEST_FILE} not found. Run create_fixtures.py first.")
        sys.exit(1)
    return json.loads(MANIFEST_FILE.read_text())


def pull_fixture(service, name: str, doc_id: str) -> dict:
    """Pull a single document and save its JSON."""
    result = service.documents().get(
        documentId=doc_id, includeTabsContent=True
    ).execute()

    output_file = FIXTURES_DIR / f"{name}.json"
    output_file.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # Summary
    title = result.get("title", "(untitled)")
    tabs = result.get("tabs", [])
    body_elements = 0
    for tab in tabs:
        body = tab.get("documentTab", {}).get("body", {})
        body_elements += len(body.get("content", []))

    print(f"  {name}: \"{title}\" — {body_elements} body elements, {len(tabs)} tab(s) → {output_file.name}")
    return result


def main():
    manifest = load_manifest()
    service = get_docs_service()

    if len(sys.argv) > 1:
        names = sys.argv[1:]
        for name in names:
            if name not in manifest:
                print(f"ERROR: '{name}' not in manifest")
                sys.exit(1)
    else:
        names = list(manifest.keys())

    print(f"Pulling {len(names)} fixture(s)...")
    for name in names:
        pull_fixture(service, name, manifest[name])

    print("Done.")


if __name__ == "__main__":
    main()
