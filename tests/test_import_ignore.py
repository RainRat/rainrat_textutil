import copy
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch
import sourcecombine
import utils


def copy_config():
    return copy.deepcopy(utils.DEFAULT_CONFIG)


def test_import_ignore_none_or_empty():
    cfg = copy_config()
    res = sourcecombine.import_ignore_patterns(None, cfg)
    assert res == cfg

    res = sourcecombine.import_ignore_patterns("non_existent.txt", None)
    assert res is None


def test_import_ignore_missing_file():
    cfg = copy_config()
    with pytest.raises(SystemExit):
        sourcecombine.import_ignore_patterns("definitely_missing_ignore_file.txt", cfg)


def test_import_ignore_empty_file(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("   \n\n# Comment only\n")
    cfg = copy_config()
    res = sourcecombine.import_ignore_patterns(empty_file, cfg)
    assert res == cfg


def test_import_ignore_text_file(tmp_path):
    text_file = tmp_path / "custom.ignore"
    text_file.write_text("# Custom ignore file\n*.tmp\nbuild/\n\n  node_modules  \n")
    cfg = copy_config()
    sourcecombine.import_ignore_patterns(text_file, cfg)
    fn_ex = cfg['filters']['exclusions']['filenames']
    assert "*.tmp" in fn_ex
    assert "build/" in fn_ex
    assert "node_modules" in fn_ex


def test_import_ignore_json_list(tmp_path):
    json_file = tmp_path / "ignore.json"
    json_file.write_text(json.dumps(["*.log", "*.bak", "dist/"]))
    cfg = copy_config()
    sourcecombine.import_ignore_patterns(json_file, cfg)
    fn_ex = cfg['filters']['exclusions']['filenames']
    assert "*.log" in fn_ex
    assert "*.bak" in fn_ex
    assert "dist/" in fn_ex


def test_import_ignore_json_dict_formats(tmp_path):
    # Dict with 'patterns'
    j1 = tmp_path / "ig1.json"
    j1.write_text(json.dumps({"patterns": ["*.cache", "temp/"]}))
    cfg1 = copy_config()
    sourcecombine.import_ignore_patterns(j1, cfg1)
    assert "*.cache" in cfg1['filters']['exclusions']['filenames']

    # Dict with 'categories'
    j2 = tmp_path / "ig2.json"
    j2.write_text(json.dumps({"categories": {"General": ["*.out"], "Build": ["target/"]}}))
    cfg2 = copy_config()
    sourcecombine.import_ignore_patterns(j2, cfg2)
    assert "*.out" in cfg2['filters']['exclusions']['filenames']
    assert "target/" in cfg2['filters']['exclusions']['filenames']

    # Dict with 'exclusions'
    j3 = tmp_path / "ig3.json"
    j3.write_text(json.dumps({"exclusions": {"filenames": ["*.swp"]}}))
    cfg3 = copy_config()
    sourcecombine.import_ignore_patterns(j3, cfg3)
    assert "*.swp" in cfg3['filters']['exclusions']['filenames']

    # Dict with list exclusions
    j4 = tmp_path / "ig4.json"
    j4.write_text(json.dumps({"exclusions": ["*.pid"]}))
    cfg4 = copy_config()
    sourcecombine.import_ignore_patterns(j4, cfg4)
    assert "*.pid" in cfg4['filters']['exclusions']['filenames']

    # Dict with 'filenames'
    j5 = tmp_path / "ig5.json"
    j5.write_text(json.dumps({"filenames": ["*.lock"]}))
    cfg5 = copy_config()
    sourcecombine.import_ignore_patterns(j5, cfg5)
    assert "*.lock" in cfg5['filters']['exclusions']['filenames']


def test_import_ignore_stdin(monkeypatch):
    cfg = copy_config()
    with patch("sys.stdin.read", return_value="*.stdin_pattern\n# comment\n"):
        sourcecombine.import_ignore_patterns("-", cfg)
    assert "*.stdin_pattern" in cfg['filters']['exclusions']['filenames']


def test_import_ignore_invalid_pattern(tmp_path):
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("valid_pattern\n")
    cfg = copy_config()

    with patch("utils.validate_glob_pattern", side_effect=utils.InvalidConfigError("invalid pattern")):
        with pytest.raises(SystemExit):
            sourcecombine.import_ignore_patterns(bad_file, cfg)


def test_import_ignore_cli_list_ignores(tmp_path, monkeypatch, capsys):
    ig_file = tmp_path / "my_ignores.txt"
    ig_file.write_text("*.imported_cli\n")

    test_args = ["sourcecombine.py", "--import-ignore", str(ig_file), "--list-ignores"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "*.imported_cli" in captured.out


def test_import_ignore_cli_combining(tmp_path, monkeypatch):
    file1 = tmp_path / "a.py"
    file1.write_text("print('hello')")
    file2 = tmp_path / "b.tmp"
    file2.write_text("temp data")

    ig_file = tmp_path / "custom.ignore"
    ig_file.write_text("*.tmp\n")

    out_file = tmp_path / "out.txt"

    test_args = ["sourcecombine.py", str(tmp_path), "--import-ignore", str(ig_file), "--output", str(out_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    sourcecombine.main()

    content = out_file.read_text()
    assert "a.py" in content
    assert "b.tmp" not in content
