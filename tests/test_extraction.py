import json
import logging
import os
import sys
import io
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import extract_files, main, _render_single_pass, _render_global_template
from utils import DEFAULT_CONFIG

def test_extract_json(tmp_path):
    output_dir = tmp_path / "extracted"

    data = [
        {"path": "src/main.py", "content": "print('hello')"},
        {"path": "README.md", "content": "# My Project"}
    ]
    content = json.dumps(data)

    extract_files(content, str(output_dir))

    assert (output_dir / "src/main.py").read_text(encoding="utf-8") == "print('hello')"
    assert (output_dir / "README.md").read_text(encoding="utf-8") == "# My Project"

def test_extract_xml(tmp_path):
    output_dir = tmp_path / "extracted"

    content = """<repository>
<file path="app.py">
import os
print("app")
</file>
<file path="config/settings.json">
{"debug": true}
</file>
</repository>"""

    extract_files(content, str(output_dir))

    # Check app.py
    assert (output_dir / "app.py").read_text(encoding="utf-8") == 'import os\nprint("app")'
    assert (output_dir / "config/settings.json").read_text(encoding="utf-8") == '{"debug": true}'

def test_extract_markdown(tmp_path):
    output_dir = tmp_path / "extracted"

    content = """# Combined Files

## src/utils.py

```python
def add(a, b):
    return a + b
```

## tests/test_utils.py

```python
from utils import add
def test_add():
    assert add(1, 1) == 2
```
"""

    extract_files(content, str(output_dir))

    assert (output_dir / "src/utils.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b"
    assert (output_dir / "tests/test_utils.py").read_text(encoding="utf-8") == "from utils import add\ndef test_add():\n    assert add(1, 1) == 2"

def test_extract_dry_run(tmp_path):
    output_dir = tmp_path / "extracted"

    data = [{"path": "file.txt", "content": "secret"}]
    content = json.dumps(data)

    extract_files(content, str(output_dir), dry_run=True)

    assert not (output_dir / "file.txt").exists()

def test_extract_security_traversal(tmp_path):
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    # Attempt to write outside the output folder
    parent_file = tmp_path / "danger.txt"
    data = [{"path": "../danger.txt", "content": "pwned"}]
    content = json.dumps(data)

    extract_files(content, str(output_dir))

    assert not parent_file.exists()
    assert not (output_dir / "../danger.txt").exists()

def test_extract_unsupported_format(tmp_path, caplog):
    content = "just some text"

    with pytest.raises(SystemExit):
        extract_files(content, str(tmp_path / "out"))

    assert "Could not find any files to extract" in caplog.text

def test_extract_text_format(tmp_path):
    """Test extraction from the default SourceCombine text format."""
    output_dir = tmp_path / "extracted"

    content = """--- file1.txt ---
Hello from file 1
--- end file1.txt ---
--- folder/file2.py ---
print("Hello from file 2")
--- end folder/file2.py ---
"""

    extract_files(content, str(output_dir))

    assert (output_dir / "file1.txt").read_text(encoding="utf-8").strip() == "Hello from file 1"
    assert (output_dir / "folder/file2.py").read_text(encoding="utf-8").strip() == 'print("Hello from file 2")'

def test_extract_flexible_markdown(tmp_path):
    """Test extraction from Markdown with different header levels and metadata."""
    output_dir = tmp_path / "extracted"

    content = """# Project Export

## src/main.py
Size: 1.2 KB
Tokens: 300

```python
print("main")
```

### config/settings.yml

```yaml
debug: true
```
"""

    extract_files(content, str(output_dir))

    assert (output_dir / "src/main.py").read_text(encoding="utf-8").strip() == 'print("main")'
    assert (output_dir / "config/settings.yml").read_text(encoding="utf-8").strip() == 'debug: true'

def test_filtered_extraction_json(tmp_path):
    output_dir = tmp_path / "output"
    archive_content = json.dumps([
        {"path": "src/main.py", "content": "print('main')"},
        {"path": "src/utils.py", "content": "print('utils')"},
        {"path": "README.md", "content": "# Readme"}
    ])

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'inclusion_groups': {
            'python': {
                'enabled': True,
                'filenames': ['*.py']
            }
        }
    }

    stats = extract_files(archive_content, output_dir, config=config)

    assert stats['total_discovered'] == 3
    assert stats['total_files'] == 2
    assert (output_dir / "src/main.py").exists()
    assert (output_dir / "src/utils.py").exists()
    assert not (output_dir / "README.md").exists()

def test_filtered_extraction_text(tmp_path):
    output_dir = tmp_path / "output"
    archive_content = (
        "--- file1.txt ---\ncontent1\n--- end file1.txt ---\n"
        "--- file2.log ---\ncontent2\n--- end file2.log ---\n"
    )

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'exclusions': {
            'filenames': ['*.log']
        }
    }

    stats = extract_files(archive_content, output_dir, config=config)

    assert stats['total_files'] == 1
    assert (output_dir / "file1.txt").exists()
    assert not (output_dir / "file2.log").exists()

def test_filtered_extraction_with_exclusion_folder(tmp_path):
    output_dir = tmp_path / "output"
    archive_content = json.dumps([
        {"path": "src/main.py", "content": "print('main')"},
        {"path": "tests/test_main.py", "content": "print('test')"},
    ])

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'exclusions': {
            'folders': ['tests']
        }
    }

    stats = extract_files(archive_content, output_dir, config=config)

    assert stats['total_files'] == 1
    assert (output_dir / "src/main.py").exists()
    assert not (output_dir / "tests/test_main.py").exists()

def test_extract_list_files(capsys, tmp_path):
    archive_content = json.dumps([
        {"path": "a.py", "content": "a"},
        {"path": "b.txt", "content": "b"}
    ])

    stats = extract_files(archive_content, tmp_path, list_files=True)

    captured = capsys.readouterr()
    assert "a.py" in captured.out
    assert "b.txt" in captured.out
    assert not (tmp_path / "a.py").exists()
    assert stats['total_files'] == 2

def test_extract_tree_view(capsys, tmp_path):
    archive_content = json.dumps([
        {"path": "src/a.py", "content": "a"},
        {"path": "docs/b.md", "content": "b"}
    ])

    stats = extract_files(archive_content, tmp_path, tree_view=True, source_name="my_archive.json")

    captured = capsys.readouterr()
    assert "my_archive.json/" in captured.out
    assert "src" in captured.out
    assert "a.py" in captured.out
    assert "docs" in captured.out
    assert "b.md" in captured.out
    assert stats['total_files'] == 2

def test_extract_xml_newline_stripping(tmp_path):
    """Verify that leading/trailing newlines in XML content are stripped."""
    output_dir = tmp_path / "extracted"

    content = """<repository>
<file path="stripped.txt">
Content with newlines
</file>
<file path="not_stripped.txt">
Already single newline</file>
</repository>"""

    extract_files(content, str(output_dir))

    assert (output_dir / "stripped.txt").read_text(encoding="utf-8") == "Content with newlines"
    assert (output_dir / "not_stripped.txt").read_text(encoding="utf-8") == "\nAlready single newline"

def test_extract_security_absolute_paths(tmp_path, caplog):
    """Verify that absolute paths are blocked during extraction."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    data = [
        {"path": "/abs/path.txt", "content": "posix"},
        {"path": "C:\\abs\\path.txt", "content": "windows"}
    ]
    content = json.dumps(data)

    with caplog.at_level(logging.WARNING):
        extract_files(content, str(output_dir))

    assert "Skipping absolute path: /abs/path.txt" in caplog.text
    assert "Skipping absolute path: C:\\abs\\path.txt" in caplog.text
    assert not (output_dir / "abs").exists()

def test_extract_security_windows_traversal(tmp_path, caplog):
    """Verify that Windows-style path traversal is blocked even on Posix."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    data = [
        {"path": "subdir\\..\\..\\danger.txt", "content": "pwned"}
    ]
    content = json.dumps(data)

    with caplog.at_level(logging.WARNING):
        extract_files(content, str(output_dir))

    assert "Skipping potentially unsafe path: subdir\\..\\..\\danger.txt" in caplog.text
    assert not (tmp_path / "danger.txt").exists()

def test_cli_extract_stdin(tmp_path, monkeypatch):
    """Test extraction from stdin via CLI."""
    output_dir = tmp_path / "extracted"

    content = """--- file1.txt ---
stdin content
--- end file1.txt ---"""

    monkeypatch.setattr('sys.stdin', io.StringIO(content))
    monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract', '-', '-o', str(output_dir)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert (output_dir / "file1.txt").read_text(encoding="utf-8").strip() == "stdin content"

def test_cli_extract_clipboard(tmp_path, monkeypatch):
    """Test extraction from clipboard via CLI."""
    output_dir = tmp_path / "extracted"

    content = """--- file_cb.txt ---
clipboard content
--- end file_cb.txt ---"""

    # Mock pyperclip
    mock_pyperclip = MagicMock()
    mock_pyperclip.paste.return_value = content
    monkeypatch.setitem(sys.modules, 'pyperclip', mock_pyperclip)

    monkeypatch.setattr('sys.argv', ['sourcecombine.py', '--extract', '--clipboard', '-o', str(output_dir)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert (output_dir / "file_cb.txt").read_text(encoding="utf-8").strip() == "clipboard content"

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

    with patch('pathlib.Path.write_text', side_effect=OSError("Write failed")):
        extract_files(content, str(output_dir))

    assert "Failed to write" in caplog.text
    assert "Write failed" in caplog.text

def test_render_single_pass_edge_cases():
    assert _render_single_pass("", {"K": "V"}) == ""
    assert _render_single_pass(None, {"K": "V"}) == ""
    assert _render_single_pass("Template", {}) == "Template"
    assert _render_single_pass("Template", None) == "Template"

def test_render_global_template_empty():
    assert _render_global_template("", {}) == ""
    assert _render_global_template(None, {}) == ""

def test_extract_xml_parse_error(tmp_path, caplog):
    """Test handling of XML parse error."""
    content = "<repository><file path='a.txt'>content</file>"
    with pytest.raises(SystemExit):
        extract_files(content, str(tmp_path))
    assert "Could not find any files to extract" in caplog.text

def test_extract_respects_size_filter(tmp_path):
    """Verify that extraction respects the max_size_bytes filter."""
    output_dir = tmp_path / "extracted"
    data = [
        {"path": "small.txt", "content": "small"},
        {"path": "large.txt", "content": "this is a much larger content"}
    ]
    content = json.dumps(data)

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'max_size_bytes': 10
    }

    stats = extract_files(content, str(output_dir), config=config)

    assert (output_dir / "small.txt").exists()
    assert not (output_dir / "large.txt").exists()
    assert stats['total_files'] == 1
    assert stats['filter_reasons']['too_large'] == 1

def test_extract_respects_binary_filter(tmp_path):
    """Verify that extraction respects the skip_binary filter."""
    output_dir = tmp_path / "extracted"
    data = [
        {"path": "text.txt", "content": "normal text"},
        {"path": "binary.bin", "content": "\x00\x01\x02binary"}
    ]
    content = json.dumps(data)

    config = DEFAULT_CONFIG.copy()
    config['filters'] = {
        'skip_binary': True
    }

    stats = extract_files(content, str(output_dir), config=config)

    assert (output_dir / "text.txt").exists()
    assert not (output_dir / "binary.bin").exists()
    assert stats['total_files'] == 1
    assert stats['filter_reasons']['binary'] == 1
