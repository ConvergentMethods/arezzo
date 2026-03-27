"""Tests for address resolver against Phase 1 fixtures."""

import json
from pathlib import Path

import pytest

from arezzo.address import resolve_address, resolve_address_range
from arezzo.errors import ArezzoAddressError
from arezzo.parser import parse_document

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def _parse(name: str):
    doc = json.loads((FIXTURES_DIR / f"{name}.json").read_text())
    return parse_document(doc)


class TestHeadingResolution:
    def test_resolve_heading_after(self):
        parsed = _parse("02_heading_hierarchy")
        idx = resolve_address(parsed, {"heading": "Section One"})
        assert idx == 80  # endIndex of "Section One" paragraph

    def test_resolve_heading_before(self):
        parsed = _parse("02_heading_hierarchy")
        idx = resolve_address(parsed, {"heading": "Section One", "position": "before"})
        assert idx == 68  # startIndex of "Section One" paragraph

    def test_resolve_heading_not_found(self):
        parsed = _parse("02_heading_hierarchy")
        with pytest.raises(ArezzoAddressError, match="not found"):
            resolve_address(parsed, {"heading": "Nonexistent Heading"})

    def test_resolve_heading_available_in_error(self):
        parsed = _parse("02_heading_hierarchy")
        with pytest.raises(ArezzoAddressError, match="Section One"):
            resolve_address(parsed, {"heading": "Nope"})

    def test_heading_range(self):
        parsed = _parse("02_heading_hierarchy")
        start, end = resolve_address_range(parsed, {"heading": "Document Title"})
        assert start == 1
        assert end == 16

    def test_kitchen_sink_headings(self):
        parsed = _parse("11_kitchen_sink")
        idx = resolve_address(parsed, {"heading": "Revenue Analysis"})
        assert idx > 0


class TestNamedRangeResolution:
    def test_resolve_named_range_start(self):
        parsed = _parse("08_named_ranges")
        idx = resolve_address(parsed, {"named_range": "introduction_section"})
        assert idx == 1

    def test_resolve_named_range_end(self):
        parsed = _parse("08_named_ranges")
        idx = resolve_address(parsed, {"named_range": "introduction_section", "position": "end"})
        assert idx == 84

    def test_named_range_bounds(self):
        parsed = _parse("08_named_ranges")
        start, end = resolve_address_range(parsed, {"named_range": "conclusion_section"})
        assert start == 84
        assert end == 157

    def test_named_range_not_found(self):
        parsed = _parse("08_named_ranges")
        with pytest.raises(ArezzoAddressError, match="not found"):
            resolve_address(parsed, {"named_range": "nonexistent"})


class TestBookmarkResolution:
    def test_bookmark_not_found(self):
        parsed = _parse("13_bookmarks")
        with pytest.raises(ArezzoAddressError, match="not found"):
            resolve_address(parsed, {"bookmark": "nonexistent_id"})

    def test_bookmark_in_plain_doc(self):
        parsed = _parse("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="not found"):
            resolve_address(parsed, {"bookmark": "any_id"})


class TestEndResolution:
    def test_end_of_document(self):
        parsed = _parse("01_plain_text")
        idx = resolve_address(parsed, {"end": True})
        # Should be startIndex of trailing empty paragraph
        assert idx == 519  # last real content ends at 519, trailing \n at 519-520

    def test_end_of_heading_doc(self):
        parsed = _parse("02_heading_hierarchy")
        idx = resolve_address(parsed, {"end": True})
        assert idx == 319


class TestStartResolution:
    def test_start_always_1(self):
        parsed = _parse("01_plain_text")
        assert resolve_address(parsed, {"start": True}) == 1

    def test_start_any_doc(self):
        parsed = _parse("05_tables")
        assert resolve_address(parsed, {"start": True}) == 1


class TestAbsoluteIndex:
    def test_valid_index(self):
        parsed = _parse("01_plain_text")
        assert resolve_address(parsed, {"index": 100}) == 100

    def test_negative_index_errors(self):
        parsed = _parse("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="Negative"):
            resolve_address(parsed, {"index": -1})

    def test_past_end_errors(self):
        parsed = _parse("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="past document end"):
            resolve_address(parsed, {"index": 99999})

    def test_zero_valid(self):
        parsed = _parse("01_plain_text")
        # Index 0 is the sectionBreak — valid but unusual
        assert resolve_address(parsed, {"index": 0}) == 0


class TestUnknownAddressMode:
    def test_unknown_mode_errors(self):
        parsed = _parse("01_plain_text")
        with pytest.raises(ArezzoAddressError, match="Unknown address mode"):
            resolve_address(parsed, {"foo": "bar"})
