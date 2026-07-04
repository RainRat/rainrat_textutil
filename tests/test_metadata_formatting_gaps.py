from sourcecombine import _format_information_summary
import pytest

def test_format_information_summary_both_present():
    meta = {'status': 'M', 'files': 1, 'size': 100}
    # [M] (1 file • 100.00 B)
    result = _format_information_summary(meta)
    assert "[M]" in result
    assert "1 file" in result
    assert "100.00 B" in result

def test_format_information_summary_only_status():
    meta = {'status': 'A'}
    result = _format_information_summary(meta)
    assert result == " [A]"

def test_format_information_summary_only_summary():
    meta = {'files': 1}
    result = _format_information_summary(meta)
    assert result == " (1 file)"

def test_format_information_summary_empty():
    meta = {}
    result = _format_information_summary(meta)
    assert result == ""

def test_format_information_summary_pluralization():
    meta = {'files': 2, 'lines': 2, 'tokens': 2}
    result = _format_information_summary(meta)
    assert "2 files" in result
    assert "2 lines" in result
    assert "2 tokens" in result

def test_format_information_summary_singular():
    meta = {'files': 1, 'lines': 1, 'tokens': 1}
    result = _format_information_summary(meta)
    assert "1 file" in result
    assert "1 line" in result
    assert "1 token" in result

def test_format_information_summary_tokens_none_or_zero():
    meta = {'tokens': None}
    result = _format_information_summary(meta)
    assert "token" not in result

    meta = {'tokens': 0}
    result = _format_information_summary(meta)
    assert "token" not in result

def test_format_information_summary_lines_zero():
    meta = {'lines': 0}
    result = _format_information_summary(meta)
    assert "line" not in result
