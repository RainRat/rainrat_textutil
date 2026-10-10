import copy
import json
import pytest
import utils
from sourcecombine import import_ignore_patterns, export_ignore_patterns


def test_import_ignore_patterns_exported_json(tmp_path):
    """Test round-trip export and import of ignore patterns using JSON."""
    export_file = tmp_path / "ignore.json"

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.tmp', '*.log', 'secret.key']

    export_ignore_patterns(export_file, config=config, json_format=True)
    assert export_file.exists()

    new_config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(export_file, new_config)

    imported = new_config['filters']['exclusions']['filenames']
    assert '*.tmp' in imported
    assert '*.log' in imported
    assert 'secret.key' in imported


def test_import_ignore_patterns_plain_text(tmp_path):
    """Test importing ignore patterns from a plain text ignore file."""
    ignore_file = tmp_path / ".customignore"
    ignore_file.write_text("""
# Comment line
*.bak
*.cache
temp_dir/
""", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(ignore_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.bak' in imported
    assert '*.cache' in imported
    assert 'temp_dir/' in imported


def test_import_ignore_patterns_json_array(tmp_path):
    """Test importing ignore patterns from a JSON array of strings."""
    ignore_file = tmp_path / "rules.json"
    data = ["*.tmp", "build_output/", "*.o"]
    ignore_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(ignore_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.tmp' in imported
    assert 'build_output/' in imported
    assert '*.o' in imported


def test_import_ignore_patterns_yaml_format(tmp_path):
    """Test importing ignore patterns from a YAML file."""
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "ignore.yml"
    yaml_content = """
exclusions:
  filenames:
    - "*.tmp"
    - "cache/"
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns(yaml_file, config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.tmp' in imported
    assert 'cache/' in imported


def test_import_ignore_patterns_stdin(monkeypatch):
    """Test importing ignore patterns from standard input ('-')."""
    data = {
        "patterns": ["*.stdin_test", "node_modules/"]
    }
    json_str = json.dumps(data)
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(json_str))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_ignore_patterns("-", config)

    imported = config['filters']['exclusions']['filenames']
    assert '*.stdin_test' in imported
    assert 'node_modules/' in imported


def test_import_ignore_patterns_missing_file(tmp_path):
    """Test error handling when the ignore import file is missing."""
    missing_file = tmp_path / "nonexistent.ignore"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_ignore_patterns(missing_file, config)


def test_import_ignore_patterns_os_error(tmp_path, monkeypatch):
    """Test error handling when file read raises OSError."""
    ignore_file = tmp_path / "unreadable.ignore"
    ignore_file.write_text("*.tmp", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_ignore_patterns(ignore_file, config)


def test_import_ignore_patterns_empty_file_and_none(tmp_path):
    """Test handling of None, empty paths, and empty files."""
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    assert import_ignore_patterns(None, config) is config
    assert import_ignore_patterns("", config) is config
    assert import_ignore_patterns("path.ignore", None) is None

    empty_file = tmp_path / "empty.ignore"
    empty_file.write_text("", encoding="utf-8")
    assert import_ignore_patterns(empty_file, config) is config


def test_cli_import_ignore_patterns(tmp_path, monkeypatch):
    """Test CLI execution with --import-ignore."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    keep_file = test_dir / "app.py"
    keep_file.write_text("print('hello')", encoding="utf-8")
    skip_file = test_dir / "app.skip_me"
    skip_file.write_text("ignore this file", encoding="utf-8")

    rules_file = tmp_path / "ignore.txt"
    rules_file.write_text("*.skip_me\n", encoding="utf-8")

    out_file = tmp_path / "output.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-ignore",
            str(rules_file),
            "--output",
            str(out_file),
        ],
    )

    from sourcecombine import main
    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "app.py" in content
    assert "app.skip_me" not in content


def test_cli_import_ig_alias(tmp_path, monkeypatch):
    """Test CLI execution with --import-ig alias."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    keep_file = test_dir / "index.js"
    keep_file.write_text("console.log(1);", encoding="utf-8")
    skip_file = test_dir / "data.temp"
    skip_file.write_text("temp data", encoding="utf-8")

    rules_file = tmp_path / "ignore.json"
    rules_file.write_text(json.dumps({"patterns": ["*.temp"]}), encoding="utf-8")

    out_file = tmp_path / "output.txt"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-ig",
            str(rules_file),
            "--output",
            str(out_file),
        ],
    )

    from sourcecombine import main
    main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "index.js" in content
    assert "data.temp" not in content


def test_import_ignore_patterns_no_valid_patterns_returns_config(tmp_path):
    ignore_file = tmp_path / "comments_only.ignore"
    ignore_file.write_text("# only comment line\n# another comment\n", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    result = import_ignore_patterns(ignore_file, config)
    assert result is config


def test_import_ignore_patterns_none_config_sections(tmp_path):
    rules_file = tmp_path / "rules.txt"
    rules_file.write_text("*.log\n", encoding="utf-8")

    config_none_filters = {"filters": None}
    import_ignore_patterns(rules_file, config_none_filters)
    assert config_none_filters["filters"]["exclusions"]["filenames"] == ["*.log"]

    config_none_exclusions = {"filters": {"exclusions": None}}
    import_ignore_patterns(rules_file, config_none_exclusions)
    assert config_none_exclusions["filters"]["exclusions"]["filenames"] == ["*.log"]

    config_none_filenames = {"filters": {"exclusions": {"filenames": None}}}
    import_ignore_patterns(rules_file, config_none_filenames)
    assert config_none_filenames["filters"]["exclusions"]["filenames"] == ["*.log"]


def test_cli_list_replacements_with_import_ignore(tmp_path, monkeypatch):
    ignore_file = tmp_path / "ignore.txt"
    ignore_file.write_text("*.tmp\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-replacements",
            "--import-ignore",
            str(ignore_file),
        ],
    )

    from sourcecombine import main
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
