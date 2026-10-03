import copy
import json
import pytest
import utils
from sourcecombine import import_ignore_patterns, export_ignore_patterns


def test_import_ignore_exported_json(tmp_path):
    """Test round-trip export and import of ignore patterns."""
    export_file = tmp_path / "exported.json"

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.log', 'temp/']

    export_ignore_patterns(export_file, config=config, json_format=True)
    assert export_file.exists()

    new_config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(export_file, new_config)

    imported = new_config['filters']['exclusions']['filenames']
    assert '*.log' in imported
    assert 'temp/' in imported


def test_import_ignore_plain_text(tmp_path):
    """Test importing ignore patterns from a standard plain text ignore file."""
    ignore_file = tmp_path / ".customignore"
    ignore_file.write_text("""
# Comment line
*.tmp
build/
  cache/

# Another comment
*.bak
""", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(ignore_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.tmp' in imported
    assert 'build/' in imported
    assert 'cache/' in imported
    assert '*.bak' in imported


def test_import_ignore_json_dict(tmp_path):
    """Test importing ignore patterns from a JSON object with various keys."""
    ignore_file = tmp_path / "patterns.json"
    data = {
        "patterns": ["*.log", "node_modules/"],
        "categories": {
            "Custom": ["*.cache"]
        }
    }
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(ignore_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.log' in imported
    assert 'node_modules/' in imported
    assert '*.cache' in imported


def test_import_ignore_json_array(tmp_path):
    """Test importing ignore patterns from a JSON array."""
    ignore_file = tmp_path / "list_patterns.json"
    data = ["*.out", "dist/", 123]
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(ignore_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.out' in imported
    assert 'dist/' in imported
    assert '123' in imported


def test_import_ignore_yaml(tmp_path):
    """Test importing ignore patterns from a YAML file."""
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "ignore.yml"
    yaml_content = """
patterns:
  - "*.pyc"
  - "__pycache__/"
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(yaml_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.pyc' in imported
    assert '__pycache__/' in imported


def test_import_ignore_stdin(monkeypatch):
    """Test importing ignore patterns from standard input ('-')."""
    text_content = "# Stdin patterns\n*.secret\nbuild/\n"
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(text_content))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns("-", config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.secret' in imported
    assert 'build/' in imported


def test_import_ignore_missing_file(tmp_path):
    """Test error handling when the ignore file is missing."""
    missing_file = tmp_path / "nonexistent.ignore"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_ignore_patterns(missing_file, config)


def test_import_ignore_empty_and_none(tmp_path):
    """Test handling of None, empty paths, and empty files."""
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    assert import_ignore_patterns(None, config) is config
    assert import_ignore_patterns("", config) is config
    assert import_ignore_patterns("path.txt", None) is None

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    assert import_ignore_patterns(empty_file, config) is config


def test_import_ignore_invalid_syntax(tmp_path):
    """Test error handling when an imported pattern file has invalid syntax or non-string pattern."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ invalid json structure", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    # Plain text fallback handles arbitrary non-empty lines, so test non-string validation
    config['filters']['exclusions']['filenames'].append(None)
    with pytest.raises(SystemExit):
        import_ignore_patterns(bad_file, config)


def test_cli_import_ignore(tmp_path, monkeypatch):
    """Test CLI execution with --import-ignore."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()

    keep_file = test_dir / "app.py"
    keep_file.write_text("print('hello')", encoding="utf-8")

    skip_file = test_dir / "secret.log"
    skip_file.write_text("sensitive data", encoding="utf-8")

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

    from sourcecombine import main
    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "app.py" in content
    assert "secret.log" not in content


def test_cli_import_ig_alias(tmp_path, monkeypatch):
    """Test CLI execution with --import-ig alias."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()

    keep_file = test_dir / "main.py"
    keep_file.write_text("print('main')", encoding="utf-8")

    skip_file = test_dir / "temp.tmp"
    skip_file.write_text("temporary", encoding="utf-8")

    ignore_file = tmp_path / "custom.ignore"
    ignore_file.write_text("*.tmp\n", encoding="utf-8")

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

    from sourcecombine import main
    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "main.py" in content
    assert "temp.tmp" not in content
