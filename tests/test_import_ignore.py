import json
import pytest
from pathlib import Path
import sourcecombine
import utils


def test_import_ignore_none_args():
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    assert sourcecombine.import_ignore_patterns(None, config) is config
    assert sourcecombine.import_ignore_patterns("dummy.txt", None) is None


def test_import_ignore_missing_file(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    missing_file = tmp_path / "non_existent_ignore.txt"
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_ignore_patterns(missing_file, config)
    assert exc_info.value.code == 1


def test_import_ignore_read_oserror(tmp_path, monkeypatch):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    target_file = tmp_path / "read_err.txt"
    target_file.write_text("pattern1\n", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_ignore_patterns(target_file, config)
    assert exc_info.value.code == 1


def test_import_ignore_empty_file(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    result = sourcecombine.import_ignore_patterns(empty_file, config)
    assert result is config


def test_import_ignore_plain_text(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    ignore_file = tmp_path / "custom_ignore.txt"
    ignore_file.write_text(
        "# Comment line\n\n*.log\nnode_modules/\n", encoding="utf-8"
    )
    result = sourcecombine.import_ignore_patterns(ignore_file, config)
    exclusions = result["filters"]["exclusions"]["filenames"]
    assert "*.log" in exclusions
    assert "node_modules/" in exclusions


def test_import_ignore_json_patterns(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    json_file = tmp_path / "patterns.json"
    data = {"patterns": ["*.tmp", "build/"]}
    json_file.write_text(json.dumps(data), encoding="utf-8")
    result = sourcecombine.import_ignore_patterns(json_file, config)
    exclusions = result["filters"]["exclusions"]["filenames"]
    assert "*.tmp" in exclusions
    assert "build/" in exclusions


def test_import_ignore_json_categories(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    json_file = tmp_path / "categories.json"
    data = {"categories": {"Group 1": ["*.bak"], "Group 2": ["*.swp"]}}
    json_file.write_text(json.dumps(data), encoding="utf-8")
    result = sourcecombine.import_ignore_patterns(json_file, config)
    exclusions = result["filters"]["exclusions"]["filenames"]
    assert "*.bak" in exclusions
    assert "*.swp" in exclusions


def test_import_ignore_json_list(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    json_file = tmp_path / "list.json"
    data = ["*.out", "dist/"]
    json_file.write_text(json.dumps(data), encoding="utf-8")
    result = sourcecombine.import_ignore_patterns(json_file, config)
    exclusions = result["filters"]["exclusions"]["filenames"]
    assert "*.out" in exclusions
    assert "dist/" in exclusions


def test_import_ignore_yaml(tmp_path):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    yaml_file = tmp_path / "patterns.yaml"
    yaml_file.write_text("patterns:\n  - '*.cache'\n  - temp/\n", encoding="utf-8")
    result = sourcecombine.import_ignore_patterns(yaml_file, config)
    exclusions = result["filters"]["exclusions"]["filenames"]
    assert "*.cache" in exclusions
    assert "temp/" in exclusions


def test_import_ignore_stdin(monkeypatch):
    config = sourcecombine.copy.deepcopy(utils.DEFAULT_CONFIG)
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO("*.stdin_ignore\nstdin_folder/\n"))
    result = sourcecombine.import_ignore_patterns("-", config)
    exclusions = result["filters"]["exclusions"]["filenames"]
    assert "*.stdin_ignore" in exclusions
    assert "stdin_folder/" in exclusions


def test_import_ignore_cli_list_ignores(tmp_path, capsys, monkeypatch):
    ignore_file = tmp_path / "cli_ignores.txt"
    ignore_file.write_text("*.custom_cli_ext\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        ["sourcecombine.py", "--import-ignore", str(ignore_file), "--list-ignores"],
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "*.custom_cli_ext" in captured


def test_import_ignore_cli_execution(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    keep_file = src_dir / "keep.py"
    keep_file.write_text("print('hello')", encoding="utf-8")
    skip_file = src_dir / "skip.custom_ext"
    skip_file.write_text("skip me", encoding="utf-8")

    ignore_file = tmp_path / "ignores.txt"
    ignore_file.write_text("*.custom_ext\n", encoding="utf-8")

    out_file = tmp_path / "combined.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(src_dir),
            "-o",
            str(out_file),
            "--import-ignore",
            str(ignore_file),
        ],
    )

    sourcecombine.main()

    content = out_file.read_text(encoding="utf-8")
    assert "keep.py" in content
    assert "skip.custom_ext" not in content
