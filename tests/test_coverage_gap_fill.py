import os
import sys
import pytest
import runpy
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_list_files_with_token_estimation_approx(tmp_path, capsys):
    """Cover sourcecombine.py line 1213: stats['token_count_is_approx'] = True in list_files mode."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("content", encoding="utf-8")

    config = {
        "search": {"root_folders": [str(root)]},
        "output": {"file": str(tmp_path / "out.txt")}
    }

    # Mock estimate_tokens to return is_approx=True
    with patch("utils.estimate_tokens", return_value=(10, True)):
        stats = sourcecombine.find_and_combine_files(
            config,
            output_path=str(tmp_path / "out.txt"),
            list_files=True,
            estimate_tokens=True,
            tree_view=False
        )

    assert stats['token_count_is_approx'] is True

def test_main_entry_point():
    """Cover sourcecombine.py line 2385: if __name__ == "__main__": main()."""
    with patch.object(sys, 'argv', ['sourcecombine.py', '--version']):
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_path("sourcecombine.py", run_name="__main__")
        assert excinfo.value.code == 0

def test_collect_file_paths_not_found(caplog):
    """Cover sourcecombine.py: collect_file_paths when folder is not found."""
    with caplog.at_level(logging.WARNING):
        paths, root, excluded = sourcecombine.collect_file_paths("non_existent_folder", recursive=True, exclude_folders=[])
    assert paths == []
    assert "not found" in caplog.text

def test_collect_file_paths_os_error_initial(tmp_path, caplog):
    """Cover sourcecombine.py: collect_file_paths when root_path.is_dir() raises OSError."""
    with patch("pathlib.Path.is_dir", side_effect=OSError("Access denied")):
        with caplog.at_level(logging.WARNING):
            paths, root, excluded = sourcecombine.collect_file_paths(str(tmp_path), recursive=True, exclude_folders=[])
    assert paths == []
    assert "Could not access" in caplog.text

def test_extract_files_empty_content(caplog):
    """Cover sourcecombine.py: extract_files with empty content."""
    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.extract_files("", "out_folder")
    assert excinfo.value.code == 1
    assert "Input content is empty" in caplog.text

def test_line_numbers_flag_in_main_coverage(tmp_path, monkeypatch):
    """Cover sourcecombine.py line 1907: --line-numbers flag in main()."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("content", encoding="utf-8")

    out_file = tmp_path / "out.txt"
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", str(root), "-o", str(out_file), "--line-numbers"])

    try:
        sourcecombine.main()
    except SystemExit as e:
        assert e.code == 0

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "1: content" in content

def test_render_template_escaping_coverage():
    """Cover sourcecombine.py: _render_template with escape_func."""
    from pathlib import Path
    from sourcecombine import _render_template

    rel_path = Path("src/a & b.txt")
    template = "File: {{FILENAME}}"

    def mock_escape(s):
        return s.replace("&", "&amp;")

    rendered = _render_template(template, rel_path, escape_func=mock_escape)
    assert rendered == "File: src/a &amp; b.txt"

def test_should_include_excluded_reason_coverage():
    """Cover sourcecombine.py line 272 and 278: return (False, 'excluded') for both filename and folder."""
    from pathlib import Path
    from sourcecombine import should_include

    # Filename exclusion
    filter_opts = {'exclusions': {'filenames': ['*.log']}}
    search_opts = {}
    rel_path = Path("test.log")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

    # Folder exclusion
    filter_opts = {'exclusions': {'folders': ['dist']}}
    rel_path = Path("dist/app.py")
    include, reason = should_include(None, rel_path, filter_opts, search_opts, return_reason=True)
    assert include is False
    assert reason == 'excluded'

def test_cli_extract_clipboard_import_error_coverage(monkeypatch, caplog):
    """Cover sourcecombine.py lines 1998-2000: pyperclip ImportError."""
    with patch.dict(sys.modules, {'pyperclip': None}):
        monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--extract', '--clipboard'])
        with pytest.raises(SystemExit) as excinfo:
            sourcecombine.main()
    assert excinfo.value.code == 1
    assert "The 'pyperclip' library is required" in caplog.text
