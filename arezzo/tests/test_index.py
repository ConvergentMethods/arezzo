"""Tests for UTF-16 index arithmetic."""

import pytest

from arezzo.errors import ArezzoIndexError
from arezzo.index import (
    sort_requests_reverse_index,
    utf16_length,
    validate_index,
    validate_not_in_surrogate,
    validate_range,
)


class TestUtf16Length:
    def test_ascii(self):
        assert utf16_length("hello") == 5

    def test_empty(self):
        assert utf16_length("") == 0

    def test_newline(self):
        assert utf16_length("hello\n") == 6

    def test_bmp_characters(self):
        # CJK characters in the Basic Multilingual Plane (U+4E00-U+9FFF)
        assert utf16_length("日本語") == 3

    def test_surrogate_pair_emoji(self):
        # 😀 is U+1F600, above U+FFFF → 2 UTF-16 code units
        assert utf16_length("😀") == 2

    def test_mixed_ascii_and_emoji(self):
        assert utf16_length("hi😀") == 4  # 2 + 2

    def test_multiple_emoji(self):
        assert utf16_length("😀😀") == 4

    def test_musical_symbol(self):
        # 𝄞 is U+1D11E (Musical Symbol G Clef) — supplementary plane
        assert utf16_length("𝄞") == 2

    def test_typical_doc_content(self):
        text = "This is a paragraph.\n"
        assert utf16_length(text) == 21

    def test_em_dash(self):
        # — is U+2014, within BMP
        assert utf16_length("—") == 1

    def test_paragraph_with_em_dash(self):
        text = "body content — plain text only.\n"
        # "body content " (13) + "—" (1) + " plain text only.\n" (19) = 33
        assert utf16_length(text) == len(text)  # all BMP, 1:1 with Python len


class TestValidateIndex:
    def test_valid(self):
        validate_index(5, 100)  # no error

    def test_zero(self):
        validate_index(0, 100)  # no error

    def test_at_end(self):
        validate_index(100, 100)  # no error — equal to end is ok

    def test_negative(self):
        with pytest.raises(ArezzoIndexError, match="Negative"):
            validate_index(-1, 100)

    def test_past_end(self):
        with pytest.raises(ArezzoIndexError, match="exceeds"):
            validate_index(101, 100)

    def test_context_in_error(self):
        with pytest.raises(ArezzoIndexError, match="insert_text"):
            validate_index(-1, 100, context="insert_text")


class TestValidateRange:
    def test_valid(self):
        validate_range(5, 10, 100)  # no error

    def test_zero_length(self):
        validate_range(5, 5, 100)  # no error — start == end is valid (empty range)

    def test_negative_start(self):
        with pytest.raises(ArezzoIndexError, match="Negative"):
            validate_range(-1, 10, 100)

    def test_end_before_start(self):
        with pytest.raises(ArezzoIndexError, match="< start"):
            validate_range(10, 5, 100)

    def test_end_past_segment(self):
        with pytest.raises(ArezzoIndexError, match="exceeds"):
            validate_range(5, 101, 100)


class TestValidateNotInSurrogate:
    def test_ascii_any_position(self):
        validate_not_in_surrogate("hello", 3)  # no error

    def test_emoji_at_start(self):
        validate_not_in_surrogate("😀hello", 0)  # no error — start of surrogate pair

    def test_emoji_after_pair(self):
        validate_not_in_surrogate("😀hello", 2)  # no error — after the pair

    def test_emoji_inside_pair(self):
        # Offset 1 falls inside the surrogate pair for 😀
        with pytest.raises(ArezzoIndexError, match="surrogate pair"):
            validate_not_in_surrogate("😀hello", 1)

    def test_multiple_emoji_boundaries(self):
        text = "😀😀"  # UTF-16: [D83D, DE00, D83D, DE00]
        validate_not_in_surrogate(text, 0)  # OK — start of first emoji
        validate_not_in_surrogate(text, 2)  # OK — start of second emoji
        with pytest.raises(ArezzoIndexError):
            validate_not_in_surrogate(text, 1)  # inside first emoji
        with pytest.raises(ArezzoIndexError):
            validate_not_in_surrogate(text, 3)  # inside second emoji

    def test_bmp_cjk_no_surrogates(self):
        # CJK in BMP — no surrogate pairs, all positions valid
        validate_not_in_surrogate("日本語", 1)  # no error


class TestSortRequestsReverseIndex:
    def test_sorts_by_index_descending(self):
        requests = [
            {"insertText": {"location": {"index": 10}, "text": "a"}},
            {"insertText": {"location": {"index": 50}, "text": "b"}},
            {"insertText": {"location": {"index": 30}, "text": "c"}},
        ]
        sorted_reqs = sort_requests_reverse_index(requests)
        indices = [r["insertText"]["location"]["index"] for r in sorted_reqs]
        assert indices == [50, 30, 10]

    def test_replace_all_text_first(self):
        requests = [
            {"insertText": {"location": {"index": 10}, "text": "a"}},
            {"replaceAllText": {"containsText": {"text": "x"}, "replaceText": "y"}},
        ]
        sorted_reqs = sort_requests_reverse_index(requests)
        assert "replaceAllText" in sorted_reqs[-1]  # lowest index (-1) goes last

    def test_range_based_requests(self):
        requests = [
            {"updateTextStyle": {"range": {"startIndex": 5, "endIndex": 10}, "textStyle": {}, "fields": "bold"}},
            {"updateTextStyle": {"range": {"startIndex": 20, "endIndex": 30}, "textStyle": {}, "fields": "bold"}},
        ]
        sorted_reqs = sort_requests_reverse_index(requests)
        assert sorted_reqs[0]["updateTextStyle"]["range"]["startIndex"] == 20

    def test_empty_list(self):
        assert sort_requests_reverse_index([]) == []

    def test_single_request(self):
        req = [{"insertText": {"location": {"index": 1}, "text": "x"}}]
        assert sort_requests_reverse_index(req) == req

    def test_table_cell_location(self):
        requests = [
            {"insertTableRow": {"tableCellLocation": {"tableStartLocation": {"index": 19}}, "insertBelow": True}},
            {"insertText": {"location": {"index": 100}, "text": "x"}},
        ]
        sorted_reqs = sort_requests_reverse_index(requests)
        assert "insertText" in sorted_reqs[0]  # index 100 > 19
