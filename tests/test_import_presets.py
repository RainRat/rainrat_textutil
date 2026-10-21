import json
import pytest
import sourcecombine
from sourcecombine import import_presets, export_presets, BUILTIN_PRESETS, PRESET_ALIASES, main


@pytest.fixture(autouse=True)
def restore_presets():
    orig_builtin = dict(sourcecombine.BUILTIN_PRESETS)
    orig_aliases = dict(sourcecombine.PRESET_ALIASES)
    yield
    sourcecombine.BUILTIN_PRESETS.clear()
    sourcecombine.BUILTIN_PRESETS.update(orig_builtin)
    sourcecombine.PRESET_ALIASES.clear()
    sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_json(tmp_path):
    preset_file = tmp_path / "custom_presets.json"
    data = {
        "presets": {
            "custom1": {
                "flag": "--custom1",
                "flags": "--line-numbers --toc",
                "description": "Custom preset 1"
            }
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    import_presets(preset_file)

    assert "custom1" in BUILTIN_PRESETS
    assert BUILTIN_PRESETS["custom1"]["flags"] == "--line-numbers --toc"
    assert PRESET_ALIASES["--custom1"] == "custom1"


def test_import_presets_yaml(tmp_path):
    yaml_file = tmp_path / "presets.yaml"
    content = """
custom_yaml:
  flag: "--custom-yaml"
  flags: "--format markdown --line-numbers"
  description: "Custom YAML preset"
"""
    yaml_file.write_text(content, encoding="utf-8")

    import_presets(yaml_file)

    assert "custom_yaml" in BUILTIN_PRESETS
    assert BUILTIN_PRESETS["custom_yaml"]["description"] == "Custom YAML preset"


def test_import_presets_stdin(monkeypatch):
    data = {
        "stdin_preset": {
            "flag": "--stdin-pre",
            "flags": "--overview",
            "description": "Preset from stdin"
        }
    }
    monkeypatch.setattr("sys.stdin.read", lambda: json.dumps(data))

    import_presets("-")

    assert "stdin_preset" in BUILTIN_PRESETS
    assert BUILTIN_PRESETS["stdin_preset"]["flags"] == "--overview"


def test_import_presets_missing_file(tmp_path, monkeypatch):
    missing_file = tmp_path / "missing.json"
    with pytest.raises(SystemExit):
        import_presets(missing_file)


def test_import_presets_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(SystemExit):
        import_presets(bad_file)


def test_import_presets_non_dict(tmp_path):
    bad_file = tmp_path / "list.json"
    bad_file.write_text("['preset1', 'preset2']", encoding="utf-8")

    with pytest.raises(SystemExit):
        import_presets(bad_file)


def test_import_presets_empty_file(tmp_path):
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")

    # Should log warning and return cleanly without exit
    import_presets(empty_file)


def test_cli_import_presets_integration(tmp_path, monkeypatch):
    preset_file = tmp_path / "presets.json"
    data = {
        "presets": {
            "cli_test": {
                "flag": "--cli-test",
                "flags": "--dry-run --estimate-tokens",
                "description": "CLI Test Preset"
            }
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["sourcecombine", "--import-presets", str(preset_file), "--preset", "cli_test", "--list-presets"])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    assert "cli_test" in BUILTIN_PRESETS
