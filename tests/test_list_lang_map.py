import json
from pathlib import Path
import pytest
from sourcecombine import main, print_lang_map


def test_print_lang_map_empty(capsys):
    print_lang_map(json_format=False)
    captured = capsys.readouterr().out
    assert "ACTIVE CUSTOM LANGUAGE MAPPINGS" in captured
    assert "No active custom language mappings configured." in captured
    assert "Total: 0 custom language mappings configured." in captured


def test_print_lang_map_json_empty(capsys):
    print_lang_map(json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 0
    assert data["custom_languages"] == {}


def test_print_lang_map_populated(capsys):
    config = {
        "search": {
            "custom_languages": {
                ".myext": "custom_lang",
                "Dockerfile.dev": "dockerfile",
            }
        }
    }
    print_lang_map(config=config, json_format=False)
    captured = capsys.readouterr().out
    assert "ACTIVE CUSTOM LANGUAGE MAPPINGS" in captured
    assert ".myext" in captured
    assert "custom_lang" in captured
    assert "Dockerfile.dev" in captured
    assert "dockerfile" in captured
    assert "Total: 2 custom language mappings configured." in captured


def test_print_lang_map_json_populated(capsys):
    config = {
        "search": {
            "custom_languages": {
                ".vue": "vue",
                ".svelte": "svelte",
            }
        }
    }
    print_lang_map(config=config, json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 2
    assert data["custom_languages"] == {
        ".svelte": "svelte",
        ".vue": "vue",
    }


def test_print_lang_map_query_filter(capsys):
    config = {
        "search": {
            "custom_languages": {
                ".pyw": "python",
                ".rs": "rust",
                ".custom": "special",
            }
        }
    }
    print_lang_map(query="py", config=config, json_format=False)
    captured = capsys.readouterr().out
    assert "FILTERED BY 'py'" in captured
    assert ".pyw" in captured
    assert "python" in captured
    assert ".rs" not in captured
    assert "special" not in captured
    assert "Matching: 1 custom language mappings configured." in captured


def test_print_lang_map_query_json(capsys):
    config = {
        "search": {
            "custom_languages": {
                ".pyw": "python",
                ".rs": "rust",
            }
        }
    }
    print_lang_map(query="rust", config=config, json_format=True)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert data["custom_languages"] == {".rs": "rust"}


def test_print_lang_map_no_match(capsys):
    config = {
        "search": {
            "custom_languages": {
                ".cpp": "cpp",
            }
        }
    }
    print_lang_map(query="ruby", config=config, json_format=False)
    captured = capsys.readouterr().out
    assert "No custom language mappings matched the filter query 'ruby'." in captured
    assert "Matching: 0 custom language mappings configured." in captured


def test_cli_list_lang_map(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "custom.yml"
    cfg_file.write_text("search:\n  custom_languages:\n    .foo: foolang\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--config",
            str(cfg_file),
            "--list-lang-map",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert ".foo" in captured
    assert "foolang" in captured


def test_cli_list_lang_mappings_alias_json(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "custom.yml"
    cfg_file.write_text("search:\n  custom_languages:\n    .bar: barlang\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--config",
            str(cfg_file),
            "--list-lang-mappings",
            "--json",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["total"] == 1
    assert data["custom_languages"] == {".bar": "barlang"}


def test_cli_list_custom_lang_alias_query(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "custom.yml"
    cfg_file.write_text(
        "search:\n  custom_languages:\n    .apple: fruit\n    .dog: animal\n"
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--config",
            str(cfg_file),
            "--list-custom-lang",
            "animal",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert ".dog" in captured
    assert "animal" in captured
    assert ".apple" not in captured


def test_cli_list_lang_map_with_import_lang_map(tmp_path, monkeypatch, capsys):
    lang_file = tmp_path / "imported_map.json"
    lang_file.write_text(json.dumps({"custom_languages": {".xyz": "xyzlang"}}))
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--import-lang-map",
            str(lang_file),
            "--list-lang-map",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert ".xyz" in captured
    assert "xyzlang" in captured


def test_cli_list_lang_map_with_import_config(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "import_cfg.yml"
    cfg_file.write_text("search:\n  custom_languages:\n    .abc: abclang\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--import-config",
            str(cfg_file),
            "--list-lang-map",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert ".abc" in captured
    assert "abclang" in captured


def test_cli_list_lang_map_config_target(tmp_path, monkeypatch, capsys):
    cfg_file = tmp_path / "custom.yml"
    cfg_file.write_text("search:\n  custom_languages:\n    .targetext: targetlang\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            str(cfg_file),
            "--list-lang-map",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert ".targetext" in captured
    assert "targetlang" in captured


def test_cli_list_lang_map_default_config_auto_detect(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    default_cfg = tmp_path / "sourcecombine.yml"
    default_cfg.write_text("search:\n  custom_languages:\n    .auto: autolang\n")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--list-lang-map",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert ".auto" in captured
    assert "autolang" in captured


def test_cli_list_lang_map_invalid_config_error(tmp_path, monkeypatch):
    invalid_cfg = tmp_path / "invalid.yml"
    invalid_cfg.write_text("search: invalid_structure")
    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--config",
            str(invalid_cfg),
            "--list-lang-map",
        ],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 1
