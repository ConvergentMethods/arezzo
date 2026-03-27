"""Tests for document parser against all 13 Phase 1 fixtures."""

import json
from pathlib import Path

import pytest

from arezzo.parser import ParsedDocument, parse_document


FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())


ALL_FIXTURES = [
    "01_plain_text",
    "02_heading_hierarchy",
    "03_inline_formatting",
    "04_lists",
    "05_tables",
    "06_images",
    "07_headers_footers_footnotes",
    "08_named_ranges",
    "09_tabs",
    "10_comments",
    "11_kitchen_sink",
    "12_horizontal_rules_page_breaks",
    "13_bookmarks",
]


class TestParseAllFixtures:
    """Every fixture must parse without errors."""

    @pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
    def test_parses_without_error(self, fixture_name):
        doc = _load(fixture_name)
        parsed = parse_document(doc)
        assert isinstance(parsed, ParsedDocument)
        assert parsed.body is not None
        assert len(parsed.body) > 0
        assert parsed.body_end_index > 0
        assert parsed.revision_id != ""

    @pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
    def test_tab_id_present(self, fixture_name):
        doc = _load(fixture_name)
        parsed = parse_document(doc)
        assert parsed.tab_id is not None
        assert parsed.tab_id == "t.0"

    @pytest.mark.parametrize("fixture_name", ALL_FIXTURES)
    def test_raw_preserved(self, fixture_name):
        doc = _load(fixture_name)
        parsed = parse_document(doc)
        assert parsed.raw is doc


class TestHeadingIndex:
    def test_heading_hierarchy(self):
        parsed = parse_document(_load("02_heading_hierarchy"))
        assert "Document Title" in parsed.heading_index
        assert "Section One" in parsed.heading_index
        assert "Section Two" in parsed.heading_index
        assert "Subsection A" in parsed.heading_index
        assert "Subsection B" in parsed.heading_index

    def test_heading_hierarchy_indices(self):
        parsed = parse_document(_load("02_heading_hierarchy"))
        # "Document Title" starts at 1, ends at 16
        entries = parsed.heading_index["Document Title"]
        assert len(entries) == 1
        start, end, heading_id = entries[0]
        assert start == 1
        assert end == 16
        assert heading_id is not None

    def test_heading_hierarchy_h2(self):
        parsed = parse_document(_load("02_heading_hierarchy"))
        entries = parsed.heading_index["Section One"]
        assert len(entries) == 1
        start, end, _ = entries[0]
        assert start == 68
        assert end == 80

    def test_no_headings_in_plain_text(self):
        parsed = parse_document(_load("01_plain_text"))
        assert len(parsed.heading_index) == 0

    def test_kitchen_sink_headings(self):
        parsed = parse_document(_load("11_kitchen_sink"))
        assert "Quarterly Business Review" in parsed.heading_index
        assert "Executive Summary" in parsed.heading_index
        assert "Revenue Analysis" in parsed.heading_index


class TestNamedRangeIndex:
    def test_named_ranges_parsed(self):
        parsed = parse_document(_load("08_named_ranges"))
        assert "introduction_section" in parsed.named_range_index
        assert "conclusion_section" in parsed.named_range_index

    def test_named_range_boundaries(self):
        parsed = parse_document(_load("08_named_ranges"))
        intro = parsed.named_range_index["introduction_section"]
        assert len(intro) == 1
        start, end, range_id = intro[0]
        assert start == 1
        assert end == 84
        assert range_id != ""

    def test_conclusion_boundaries(self):
        parsed = parse_document(_load("08_named_ranges"))
        conclusion = parsed.named_range_index["conclusion_section"]
        start, end, _ = conclusion[0]
        assert start == 84
        assert end == 157

    def test_no_named_ranges_in_plain_text(self):
        parsed = parse_document(_load("01_plain_text"))
        assert len(parsed.named_range_index) == 0


class TestSegments:
    def test_headers_parsed(self):
        parsed = parse_document(_load("07_headers_footers_footnotes"))
        assert len(parsed.headers) > 0

    def test_footers_parsed(self):
        parsed = parse_document(_load("07_headers_footers_footnotes"))
        assert len(parsed.footers) > 0

    def test_footnotes_parsed(self):
        parsed = parse_document(_load("07_headers_footers_footnotes"))
        assert len(parsed.footnotes) > 0

    def test_lists_parsed(self):
        parsed = parse_document(_load("04_lists"))
        assert len(parsed.lists) == 3  # bullet, numbered, nested

    def test_inline_objects_parsed(self):
        parsed = parse_document(_load("06_images"))
        assert len(parsed.inline_objects) > 0

    def test_no_segments_in_plain_text(self):
        parsed = parse_document(_load("01_plain_text"))
        assert len(parsed.headers) == 0
        assert len(parsed.footers) == 0
        assert len(parsed.footnotes) == 0


class TestBodyEndIndex:
    def test_plain_text_end(self):
        parsed = parse_document(_load("01_plain_text"))
        # Last element is trailing \n paragraph at 519-520
        assert parsed.body_end_index == 520

    def test_heading_doc_end(self):
        parsed = parse_document(_load("02_heading_hierarchy"))
        assert parsed.body_end_index == 320


class TestEdgeCases:
    def test_empty_tabs_raises(self):
        with pytest.raises(ValueError, match="no tabs"):
            parse_document({"tabs": []})

    def test_missing_tabs_raises(self):
        with pytest.raises(ValueError, match="no tabs"):
            parse_document({})

    def test_proto3_default_omission(self):
        """Headers/footers have startIndex=0 omitted from JSON."""
        parsed = parse_document(_load("07_headers_footers_footnotes"))
        # Header content should be accessible
        for hid, header in parsed.headers.items():
            content = header.get("content", [])
            assert len(content) > 0
            # First element may have startIndex omitted (proto3 default)
            first = content[0]
            start = first.get("startIndex", 0)
            assert start == 0
