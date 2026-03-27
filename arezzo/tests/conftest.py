"""Shared test fixtures — loads Phase 1 JSON fixtures."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"
MUTATIONS_DIR = FIXTURES_DIR / "mutations"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def mutations_dir():
    return MUTATIONS_DIR


def _load_fixture(name: str) -> dict:
    path = FIXTURES_DIR / f"{name}.json"
    return json.loads(path.read_text())


@pytest.fixture
def plain_text_doc():
    return _load_fixture("01_plain_text")


@pytest.fixture
def heading_doc():
    return _load_fixture("02_heading_hierarchy")


@pytest.fixture
def formatting_doc():
    return _load_fixture("03_inline_formatting")


@pytest.fixture
def lists_doc():
    return _load_fixture("04_lists")


@pytest.fixture
def tables_doc():
    return _load_fixture("05_tables")


@pytest.fixture
def images_doc():
    return _load_fixture("06_images")


@pytest.fixture
def headers_footers_doc():
    return _load_fixture("07_headers_footers_footnotes")


@pytest.fixture
def named_ranges_doc():
    return _load_fixture("08_named_ranges")


@pytest.fixture
def tabs_doc():
    return _load_fixture("09_tabs")


@pytest.fixture
def comments_doc():
    return _load_fixture("10_comments")


@pytest.fixture
def kitchen_sink_doc():
    return _load_fixture("11_kitchen_sink")


@pytest.fixture
def page_breaks_doc():
    return _load_fixture("12_horizontal_rules_page_breaks")


@pytest.fixture
def bookmarks_doc():
    return _load_fixture("13_bookmarks")


def load_mutation(operation_name: str) -> dict:
    """Load a mutation pair: before, request, after, description."""
    op_dir = MUTATIONS_DIR / operation_name
    return {
        "before": json.loads((op_dir / "before.json").read_text()),
        "request": json.loads((op_dir / "request.json").read_text()),
        "after": json.loads((op_dir / "after.json").read_text()),
        "description": (op_dir / "description.md").read_text(),
    }
