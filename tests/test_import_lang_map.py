import copy
import json
import logging
import sys
from pathlib import Path
import pytest

import utils
import sourcecombine
from sourcecombine import import_lang_map, export_lang_map


def test_import_lang_map_exported_json(tmp_path):
    """Test round-trip export and import of custom language mappings."""
    export_file = tmp_path / "lang_map.json"

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['search']['custom_languages'] = {
        '.mjml': 'html',
        '.blade.php': 'php'
    }

    export_lang_map(export_file, config=config)
    assert export_file.exists()

    new_config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(export_file, new_config)

    assert new_config['search']['custom_languages'] == {
        '.mjml': 'html',
        '.blade.php': 'php'
    }


def test_import_lang_map_direct_dict(tmp_path):
    """Test importing language mappings from a direct dictionary JSON file."""
    map_file = tmp_path / "direct_map.json"
    data = {
        ".vue": "html",
        ".svelte": "html"
    }
    map_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(map_file, config)

    assert config['search']['custom_languages']['.vue'] == 'html'
    assert config['search']['custom_languages']['.svelte'] == 'html'


def test_import_lang_map_nested_keys(tmp_path):
    """Test importing language mappings with language_mappings or lang_map keys."""
    map_file1 = tmp_path / "lang_map1.json"
    map_file1.write_text(json.dumps({"language_mappings": {".astro": "html"}}), encoding="utf-8")

    config1 = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(map_file1, config1)
    assert config1['search']['custom_languages']['.astro'] == 'html'

    map_file2 = tmp_path / "lang_map2.json"
    map_file2.write_text(json.dumps({"lang_map": {".pcss": "css"}}), encoding="utf-8")

    config2 = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(map_file2, config2)
    assert config2['search']['custom_languages']['.pcss'] == 'css'


def test_import_lang_map_list_of_dicts(tmp_path):
    """Test importing language mappings from a list of dictionary items."""
    map_file = tmp_path / "list_map.json"
    data = [
        {"extension": ".mjml", "language": "html"},
        {"pattern": ".blade.php", "lang": "php"}
    ]
    map_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(map_file, config)

    assert config['search']['custom_languages']['.mjml'] == 'html'
    assert config['search']['custom_languages']['.blade.php'] == 'php'


def test_import_lang_map_list_of_pairs(tmp_path):
    """Test importing language mappings from a list of key-value pairs."""
    map_file = tmp_path / "pairs_map.json"
    data = [
        [".mjml", "html"],
        [".jsx", "javascript"]
    ]
    map_file.write_text(json.dumps(data), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(map_file, config)

    assert config['search']['custom_languages']['.mjml'] == 'html'
    assert config['search']['custom_languages']['.jsx'] == 'javascript'


def test_import_lang_map_yaml_format(tmp_path):
    """Test importing language mappings from a YAML file."""
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "lang.yml"
    yaml_content = """
custom_languages:
  .mjml: html
  .blade.php: php
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(yaml_file, config)

    assert config['search']['custom_languages']['.mjml'] == 'html'
    assert config['search']['custom_languages']['.blade.php'] == 'php'


def test_import_lang_map_stdin(monkeypatch):
    """Test importing language mappings from standard input ('-')."""
    data = {".mjml": "html"}
    json_str = json.dumps(data)
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(json_str))

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map("-", config)

    assert config['search']['custom_languages']['.mjml'] == 'html'


def test_import_lang_map_language_tag_processing(tmp_path):
    """Test that imported mappings affect utils.get_language_tag."""
    map_file = tmp_path / "lang.json"
    map_file.write_text(json.dumps({".customext": "python"}), encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    import_lang_map(map_file, config)

    tag = utils.get_language_tag("file.customext", overrides=config['search']['custom_languages'])
    assert tag == "python"


def test_import_lang_map_missing_file(tmp_path):
    """Test error handling when the language map file is missing."""
    missing_file = tmp_path / "nonexistent.json"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    with pytest.raises(SystemExit):
        import_lang_map(missing_file, config)


def test_import_lang_map_invalid_syntax(tmp_path):
    """Test error handling when language map file has invalid syntax."""
    bad_file = tmp_path / "bad_syntax.json"
    bad_file.write_text("{ this is not valid json or yaml", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        import_lang_map(bad_file, config)


def test_import_lang_map_invalid_format(tmp_path):
    """Test error handling when format is not dict or list."""
    bad_file = tmp_path / "number.json"
    bad_file.write_text("12345", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    with pytest.raises(SystemExit):
        import_lang_map(bad_file, config)


def test_import_lang_map_empty_file_and_none(tmp_path):
    """Test handling of None, empty paths, and empty files."""
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    assert import_lang_map(None, config) is config
    assert import_lang_map("", config) is config
    assert import_lang_map("lang.json", None) is None

    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    assert import_lang_map(empty_file, config) is config


def test_cli_import_lang_map(tmp_path, monkeypatch):
    """Test CLI execution with --import-lang-map."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    sample_file = test_dir / "template.mjml"
    sample_file.write_text("<mjml></mjml>", encoding="utf-8")

    map_file = tmp_path / "lang.json"
    map_file.write_text(json.dumps({".mjml": "html"}), encoding="utf-8")

    out_file = tmp_path / "output.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-lang-map",
            str(map_file),
            "--format",
            "markdown",
            "--output",
            str(out_file),
        ],
    )

    from sourcecombine import main
    main()

    assert out_file.exists()
    assert "```html" in out_file.read_text(encoding="utf-8").lower()


def test_cli_import_lang_alias(tmp_path, monkeypatch):
    """Test CLI execution with --import-lang alias."""
    test_dir = tmp_path / "src"
    test_dir.mkdir()
    sample_file = test_dir / "template.mjml"
    sample_file.write_text("<mjml></mjml>", encoding="utf-8")

    map_file = tmp_path / "lang.json"
    map_file.write_text(json.dumps({".mjml": "html"}), encoding="utf-8")

    out_file = tmp_path / "output.md"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(test_dir),
            "--import-lang",
            str(map_file),
            "--format",
            "markdown",
            "--output",
            str(out_file),
        ],
    )

    from sourcecombine import main
    main()

    assert out_file.exists()
    assert "```html" in out_file.read_text(encoding="utf-8").lower()


def test_cli_import_lang_map_and_files_from_conflict(monkeypatch, caplog):
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine", "--import-lang-map", "lang.json", "--files-from", "list.txt"]
    )

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1
    assert "cannot use --import-lang-map and --files-from at the same time" in caplog.text
