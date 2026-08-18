"""Regression tests for tools/add_line_numbers.py line-splitting behavior."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.add_line_numbers import number_in_place, numbered_text, split_lines


def test_split_lines_ignores_non_newline_unicode_boundaries():
    text = "Section A\nSome text\x0cSection B\nMore text\n"
    assert split_lines(text) == ["Section A", "Some text\x0cSection B", "More text"]


def test_numbered_text_preserves_embedded_form_feed():
    text = "Section A\nSome text\x0cSection B\nMore text\n"
    result = numbered_text(text, 4)
    assert "\x0c" in result
    assert result == "L0001 | Section A\nL0002 | Some text\x0cSection B\nL0003 | More text\n"


def test_numbered_text_preserves_embedded_line_separator():
    text = "a\n b\n"
    result = numbered_text(text, 4)
    assert " " in result
    assert result == "L0001 | a\nL0002 |  b\n"


def test_numbered_text_line_count_matches_real_newlines():
    text = "a\x0bb\nc\n"
    result = numbered_text(text, 4)
    assert result.count("\n") == 2
    assert "L0003" not in result


def test_numbered_text_handles_crlf():
    text = "a\r\nb\r\n"
    assert numbered_text(text, 4) == "L0001 | a\r\nL0002 | b\r\n"


def test_numbered_text_handles_no_trailing_newline():
    assert numbered_text("a\nb", 4) == "L0001 | a\nL0002 | b"


def test_split_lines_empty_text():
    assert split_lines("") == []


def test_number_in_place_does_not_corrupt_form_feed(tmp_path):
    target = tmp_path / "doc.txt"
    target.write_text("Section A\nSome text\x0cSection B\n", encoding="utf-8")
    changed = number_in_place(target, width=4, force=False)
    assert changed is True
    result = target.read_text(encoding="utf-8")
    assert "\x0c" in result
    assert result == "L0001 | Section A\nL0002 | Some text\x0cSection B\n"
