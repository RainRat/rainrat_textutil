import json
import logging
from pathlib import Path
import pytest
import sys
import io
from unittest.mock import patch, MagicMock

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import extract_files, main, _render_single_pass, _render_global_template

def test_render_single_pass_edge_cases():
    """Cover edge cases in _render_single_pass."""
    assert _render_single_pass("", {"K": "V"}) == ""
    assert _render_single_pass(None, {"K": "V"}) == ""
    assert _render_single_pass("Template", {}) == "Template"
    assert _render_single_pass("Template", None) == "Template"

def test_render_global_template_empty():
    """Cover empty template in _render_global_template."""
    assert _render_global_template("", {}) == ""
    assert _render_global_template(None, {}) == ""

def test_extract_xml_newline_stripping(tmp_path):
    """Verify that leading/trailing newlines in XML content are stripped."""
    output_dir = tmp_path / "extracted"

    # Content has leading and trailing newlines within <file> tag
    content = """<repository>
<file path="stripped.txt">
Content with newlines
</file>
<file path="not_stripped.txt">
Already single newline</file>
</repository>"""

    extract_files(content, str(output_dir))

    # stripped.txt should have the first \n and last \n removed
    # The actual text in ET for stripped.txt is "\nContent with newlines\n"
    assert (output_dir / "stripped.txt").read_text(encoding="utf-8") == "Content with newlines"

    # not_stripped.txt has "\nAlready single newline"
    # It starts with \n but doesn't end with \n, so it's NOT stripped by the logic
    assert (output_dir / "not_stripped.txt").read_text(encoding="utf-8") == "\nAlready single newline"

def test_extract_security_absolute_paths(tmp_path, caplog):
    """Verify that absolute paths are blocked during extraction."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    # Try both Posix and Windows absolute paths
    data = [
        {"path": "/abs/path.txt", "content": "posix"},
        {"path": "C:\\abs\\path.txt", "content": "windows"}
    ]
    content = json.dumps(data)

    with caplog.at_level(logging.WARNING):
        extract_files(content, str(output_dir))

    assert "Skipping potentially unsafe path: /abs/path.txt" in caplog.text
    assert "Skipping potentially unsafe path: C:\\abs\\path.txt" in caplog.text
    assert not (output_dir / "abs").exists()

def test_extract_security_windows_traversal(tmp_path, caplog):
    """Verify that Windows-style path traversal is blocked even on Posix."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    # Try Windows-style traversal
    data = [
        {"path": "subdir\\..\\..\\danger.txt", "content": "pwned"}
    ]
    content = json.dumps(data)

    with caplog.at_level(logging.WARNING):
        extract_files(content, str(output_dir))

    assert "Skipping potentially unsafe path: subdir\\..\\..\\danger.txt" in caplog.text
    assert not (tmp_path / "danger.txt").exists()

def test_cli_extract_stdin(tmp_path, monkeypatch, caplog):
    """Test extraction from stdin via CLI."""
    output_dir = tmp_path / "extracted"

    content = """--- file1.txt ---
stdin content
--- end file1.txt ---"""

    # Mock sys.stdin.read
    monkeypatch.setattr('sys.stdin', io.StringIO(content))
    # Mock sys.argv
    monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract', '-', '-o', str(output_dir)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert (output_dir / "file1.txt").read_text(encoding="utf-8").strip() == "stdin content"

def test_cli_extract_clipboard(tmp_path, monkeypatch, caplog):
    """Test extraction from clipboard via CLI."""
    output_dir = tmp_path / "extracted"

    content = """--- file_cb.txt ---
clipboard content
--- end file_cb.txt ---"""

    # Mock pyperclip
    mock_pyperclip = MagicMock()
    mock_pyperclip.paste.return_value = content
    monkeypatch.setitem(sys.modules, 'pyperclip', mock_pyperclip)

    # Mock sys.argv
    monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract', '--clipboard', '-o', str(output_dir)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert (output_dir / "file_cb.txt").read_text(encoding="utf-8").strip() == "clipboard content"

def test_cli_extract_clipboard_import_error(monkeypatch, caplog):
    """Test handling of missing pyperclip during clipboard extraction."""
    # Simulate ImportError for pyperclip
    with patch.dict(sys.modules, {'pyperclip': None}):
        monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract', '--clipboard'])
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "The 'pyperclip' library is required" in caplog.text

def test_cli_extract_file_not_found(caplog, monkeypatch):
    """Test extraction with non-existent input file."""
    monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract', 'non_existent_file.txt'])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    assert "Input file not found" in caplog.text

def test_cli_extract_no_input(caplog, monkeypatch):
    """Test extraction with no input specified."""
    monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract'])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    assert "No input specified for extraction" in caplog.text

def test_extract_write_failure(tmp_path, caplog):
    """Test handling of OSError during file write in extraction."""
    output_dir = tmp_path / "extracted"
    content = json.dumps([{"path": "fail.txt", "content": "data"}])

    # Mock target_path.write_text to raise OSError
    with patch('pathlib.Path.write_text', side_effect=OSError("Write failed")):
        extract_files(content, str(output_dir))

    assert "Failed to write" in caplog.text
    assert "Write failed" in caplog.text

def test_extract_xml_parse_error(tmp_path, caplog):
    """Test handling of XML parse error (should just fall through to other formats)."""
    # Invalid XML
    content = "<repository><file path='a.txt'>content</file>"
    # This will fail ET.fromstring but it shouldn't crash extract_files
    # It will then try Text and Markdown.

    with pytest.raises(SystemExit):
        extract_files(content, str(tmp_path))

    assert "Could not find any files to extract" in caplog.text
