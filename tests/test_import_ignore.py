import json
import pytest
import sys
import copy
from pathlib import Path
from unittest.mock import patch

import sourcecombine
import utils


def test_import_ignore_none_or_empty_path():
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    res = sourcecombine.import_ignore_patterns(None, config)
    assert res == config

    res2 = sourcecombine.import_ignore_patterns("", config)
    assert res2 == config


def test_import_ignore_none_config():
    res = sourcecombine.import_ignore_patterns("some_file.txt", None)
    assert res is None


def test_import_ignore_text_file(tmp_path):
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("# Comment line\n*.tmp\n\n  *.log  \n# Another comment\ntemp_folder/*\n")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_ignore_patterns(str(ignore_file), config)

    fn_ex = config['filters']['exclusions']['filenames']
    assert "*.tmp" in fn_ex
    assert "*.log" in fn_ex
    assert "temp_folder/*" in fn_ex


def test_import_ignore_json_list(tmp_path):
    ignore_file = tmp_path / "ignore.json"
    ignore_file.write_text(json.dumps(["*.bak", "*.swp", "  node_modules/*  "]))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_ignore_patterns(str(ignore_file), config)

    fn_ex = config['filters']['exclusions']['filenames']
    assert "*.bak" in fn_ex
    assert "*.swp" in fn_ex
    assert "node_modules/*" in fn_ex


def test_import_ignore_json_dict_patterns(tmp_path):
    ignore_file = tmp_path / "ignore.json"
    ignore_file.write_text(json.dumps({
        "patterns": ["*.cache", "build_output/*"]
    }))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_ignore_patterns(str(ignore_file), config)

    fn_ex = config['filters']['exclusions']['filenames']
    assert "*.cache" in fn_ex
    assert "build_output/*" in fn_ex


def test_import_ignore_yaml(tmp_path):
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    ignore_file = tmp_path / "ignore.yaml"
    ignore_file.write_text("ignore_patterns:\n  - '*.yaml_tmp'\n  - 'dist_yaml/*'\n")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_ignore_patterns(str(ignore_file), config)

    fn_ex = config['filters']['exclusions']['filenames']
    assert "*.yaml_tmp" in fn_ex
    assert "dist_yaml/*" in fn_ex


def test_import_ignore_stdin(monkeypatch):
    input_text = "*.stdin_ignore\n# comment\n  stdin_dir/*  "
    monkeypatch.setattr(sys, 'stdin', pytest.importorskip("io").StringIO(input_text))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_ignore_patterns("-", config)

    fn_ex = config['filters']['exclusions']['filenames']
    assert "*.stdin_ignore" in fn_ex
    assert "stdin_dir/*" in fn_ex


def test_import_ignore_empty_file(tmp_path):
    ignore_file = tmp_path / "empty.txt"
    ignore_file.write_text("   \n\n# Only comments\n")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    sourcecombine.import_ignore_patterns(str(ignore_file), config)
    # Shouldn't raise error, config unchanged


def test_import_ignore_missing_file():
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_ignore_patterns("non_existent_file_xyz.txt", config)
    assert exc.value.code == 1


def test_import_ignore_os_error(tmp_path, monkeypatch):
    ignore_file = tmp_path / "unreadable.txt"
    ignore_file.write_text("data")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit) as exc:
        sourcecombine.import_ignore_patterns(str(ignore_file), config)
    assert exc.value.code == 1


def test_import_ignore_cli_integration(tmp_path, monkeypatch, capsys):
    ignore_file = tmp_path / "cli_patterns.txt"
    ignore_file.write_text("*.custom_cli_ext\ncustom_cli_folder/*\n")

    test_args = ["sourcecombine.py", "--import-ig", str(ignore_file), "--list-ig"]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0

    captured = capsys.readouterr().out
    assert "*.custom_cli_ext" in captured
    assert "custom_cli_folder/*" in captured
