import json
import os
import sys
import pytest
from unittest.mock import patch
import sourcecombine
import utils


def test_import_ignore_patterns_none_inputs():
    assert sourcecombine.import_ignore_patterns(None, {}) == {}
    assert sourcecombine.import_ignore_patterns("file.txt", None) is None


def test_import_ignore_patterns_text_file(tmp_path):
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("# Comment line\n*.log\n\ntemp/\n# Another comment\nbuild/*\n", encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(str(ignore_file), config)

    filenames = config["filters"]["exclusions"]["filenames"]
    assert "*.log" in filenames
    assert "temp/" in filenames
    assert "build/*" in filenames


def test_import_ignore_patterns_json_list(tmp_path):
    ignore_file = tmp_path / "ignores.json"
    ignore_file.write_text(json.dumps(["*.bak", "*.tmp"]), encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(str(ignore_file), config)

    filenames = config["filters"]["exclusions"]["filenames"]
    assert "*.bak" in filenames
    assert "*.tmp" in filenames


def test_import_ignore_patterns_json_dict_formats(tmp_path):
    # Test dictionary formats (patterns, active_ignore_patterns, ignore_patterns, categories)
    dict_patterns = tmp_path / "dict_pats.json"
    dict_patterns.write_text(json.dumps({"patterns": ["*.a"]}), encoding="utf-8")

    dict_active = tmp_path / "dict_active.json"
    dict_active.write_text(json.dumps({"active_ignore_patterns": ["*.b"]}), encoding="utf-8")

    dict_ig = tmp_path / "dict_ig.json"
    dict_ig.write_text(json.dumps({"ignore_patterns": ["*.c"]}), encoding="utf-8")

    dict_cats = tmp_path / "dict_cats.json"
    dict_cats.write_text(json.dumps({"categories": {"cat1": ["*.d"], "cat2": ["*.e"]}}), encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(str(dict_patterns), config)
    sourcecombine.import_ignore_patterns(str(dict_active), config)
    sourcecombine.import_ignore_patterns(str(dict_ig), config)
    sourcecombine.import_ignore_patterns(str(dict_cats), config)

    filenames = config["filters"]["exclusions"]["filenames"]
    assert "*.a" in filenames
    assert "*.b" in filenames
    assert "*.c" in filenames
    assert "*.d" in filenames
    assert "*.e" in filenames


def test_import_ignore_patterns_stdin(monkeypatch):
    stdin_content = "# Header\n*.out\n*.pid\n"
    monkeypatch.setattr(sys, "stdin", io_StringIO(stdin_content))

    config = copy_config()
    sourcecombine.import_ignore_patterns("-", config)

    filenames = config["filters"]["exclusions"]["filenames"]
    assert "*.out" in filenames
    assert "*.pid" in filenames


def test_import_ignore_patterns_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("   \n\n# Only comments\n", encoding="utf-8")

    config = copy_config()
    sourcecombine.import_ignore_patterns(str(empty_file), config)
    assert "empty" in caplog.text.lower() or "no rules imported" in caplog.text.lower() or "no valid ignore patterns" in caplog.text.lower()


def test_import_ignore_patterns_nonexistent_file():
    config = copy_config()
    with pytest.raises(SystemExit):
        sourcecombine.import_ignore_patterns("nonexistent_file_12345.ignore", config)


def test_import_ignore_patterns_os_error(tmp_path, monkeypatch):
    p = tmp_path / "error.ignore"
    p.write_text("*.log", encoding="utf-8")

    config = copy_config()

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    with pytest.raises(SystemExit):
        sourcecombine.import_ignore_patterns(str(p), config)


def test_import_ignore_cli_list_ignores(tmp_path, capsys):
    ignore_file = tmp_path / "test.ignore"
    ignore_file.write_text("custom_imported_pattern_xyz.log\n", encoding="utf-8")

    test_args = ["sourcecombine.py", "--import-ignore", str(ignore_file), "--list-ignores"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "custom_imported_pattern_xyz.log" in captured.out


def test_import_ignore_cli_files_from_collision(tmp_path):
    test_args = ["sourcecombine.py", "--files-from", "-", "--import-ignore", "-"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()
        assert exc_info.value.code == 1


def copy_config():
    import copy
    cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
    utils.validate_config(cfg)
    return cfg


class io_StringIO:
    def __init__(self, text):
        self.text = text
    def read(self):
        return self.text
