import copy
import json
import pytest
import utils
from sourcecombine import import_ignore_patterns, export_ignore_patterns, main


def test_import_ignore_patterns_text_file(tmp_path):
    """Test importing ignore patterns from a plain text file."""
    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("# Comment line\n*.log\n\nbuild/\n*.tmp\n", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(ignore_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.log" in filenames
    assert "build/" in filenames
    assert "*.tmp" in filenames


def test_import_ignore_patterns_exported_json(tmp_path):
    """Test round-trip export and import of ignore patterns."""
    export_file = tmp_path / "exported_ignore.json"

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ["*.cache", "temp/"]

    export_ignore_patterns(export_file, config=config, json_format=True)
    assert export_file.exists()

    new_config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(export_file, new_config)

    filenames = new_config['filters']['exclusions']['filenames']
    assert "*.cache" in filenames
    assert "temp/" in filenames


def test_import_ignore_patterns_json_array_and_dict(tmp_path):
    """Test importing ignore patterns from JSON array and dict structures."""
    json_list_file = tmp_path / "list_ignore.json"
    json_list_file.write_text(json.dumps(["*.bak", "*.swp"]), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(json_list_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.bak" in filenames
    assert "*.swp" in filenames

    json_dict_file = tmp_path / "dict_ignore.json"
    json_dict_file.write_text(json.dumps({"ignore_patterns": ["*.out", "dist/"]}), encoding="utf-8")

    import_ignore_patterns(json_dict_file, config)
    filenames = config['filters']['exclusions']['filenames']
    assert "*.out" in filenames
    assert "dist/" in filenames


def test_import_ignore_patterns_yaml_format(tmp_path):
    """Test importing ignore patterns from a YAML file."""
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "ignore.yml"
    yaml_content = """
patterns:
  - "*.generated"
  - "coverage/"
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(yaml_file, config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.generated" in filenames
    assert "coverage/" in filenames


def test_import_ignore_patterns_stdin(monkeypatch):
    """Test importing ignore patterns from standard input ('-')."""
    ignore_lines = "# Stdin ignore\n*.pyc\n__pycache__/\n"
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(ignore_lines))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns("-", config)

    filenames = config['filters']['exclusions']['filenames']
    assert "*.pyc" in filenames
    assert "__pycache__/" in filenames


def test_import_ignore_patterns_none_and_empty(tmp_path):
    """Test handling of None path, None config, and empty files."""
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    assert import_ignore_patterns(None, config) is config
    assert import_ignore_patterns("", config) is config
    assert import_ignore_patterns("file.txt", None) is None

    empty_file = tmp_path / "empty.ignore"
    empty_file.write_text("", encoding="utf-8")
    assert import_ignore_patterns(empty_file, config) is config


def test_import_ignore_patterns_missing_file(tmp_path):
    """Test error handling when ignore file is missing."""
    missing = tmp_path / "missing.ignore"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_ignore_patterns(missing, config)


def test_cli_import_ignore(tmp_path, monkeypatch):
    """Test CLI execution with --import-ignore."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    keep_file = test_dir / "keep.py"
    keep_file.write_text("print('keep')", encoding="utf-8")
    ignore_target = test_dir / "ignore_me.log"
    ignore_target.write_text("log data", encoding="utf-8")

    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("*.log\n", encoding="utf-8")

    out_file = tmp_path / "output.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-ignore",
            str(ignore_file),
            "--output",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "keep.py" in content
    assert "ignore_me.log" not in content


def test_cli_import_ig_alias(tmp_path, monkeypatch):
    """Test CLI execution with --import-ig alias."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    file_a = test_dir / "file_a.txt"
    file_a.write_text("Content A", encoding="utf-8")
    file_b = test_dir / "file_b.tmp"
    file_b.write_text("Content B", encoding="utf-8")

    ignore_file = tmp_path / "rules.json"
    ignore_file.write_text(json.dumps(["*.tmp"]), encoding="utf-8")

    out_file = tmp_path / "output.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-ig",
            str(ignore_file),
            "--output",
            str(out_file),
        ],
    )

    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "file_a.txt" in content
    assert "file_b.tmp" not in content


def test_cli_stdin_collision(monkeypatch, caplog):
    """Test error when reading both --files-from and --import-ignore from stdin."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--files-from",
            "-",
            "--import-ignore",
            "-",
        ],
    )

    with pytest.raises(SystemExit):
        main()

    assert "You cannot read both --files-from and --import-ignore from standard input" in caplog.text
