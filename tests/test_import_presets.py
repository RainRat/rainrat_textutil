import io
import json
import logging
import pytest
import sys
import sourcecombine
import utils


def test_import_presets_json_file(tmp_path, monkeypatch):
    preset_data = {
        "presets": {
            "custom_json": {
                "flag": "--custom-json, -cj",
                "flags": "--format json --compact",
                "description": "Custom JSON preset for testing."
            }
        }
    }
    preset_file = tmp_path / "custom_presets.json"
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    # Restore BUILTIN_PRESETS and PRESET_ALIASES after test
    orig_builtin = sourcecombine.BUILTIN_PRESETS.copy()
    orig_aliases = sourcecombine.PRESET_ALIASES.copy()

    try:
        sourcecombine.import_presets(preset_file)
        assert "custom_json" in sourcecombine.BUILTIN_PRESETS
        assert sourcecombine.BUILTIN_PRESETS["custom_json"]["flags"] == "--format json --compact"
        assert sourcecombine.PRESET_ALIASES.get("custom_json") == "custom_json"
        assert sourcecombine.PRESET_ALIASES.get("--custom-json") == "custom_json"
        assert sourcecombine.PRESET_ALIASES.get("-cj") == "custom_json"
    finally:
        sourcecombine.BUILTIN_PRESETS.clear()
        sourcecombine.BUILTIN_PRESETS.update(orig_builtin)
        sourcecombine.PRESET_ALIASES.clear()
        sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_yaml_file(tmp_path):
    if not utils.yaml:
        pytest.skip("PyYAML is not installed.")

    yaml_content = """
presets:
  custom_yaml:
    flag: "--custom-yaml"
    flags: "--format markdown --line-numbers"
    description: "Custom YAML preset."
"""
    preset_file = tmp_path / "custom_presets.yml"
    preset_file.write_text(yaml_content, encoding="utf-8")

    orig_builtin = sourcecombine.BUILTIN_PRESETS.copy()
    orig_aliases = sourcecombine.PRESET_ALIASES.copy()

    try:
        sourcecombine.import_presets(preset_file)
        assert "custom_yaml" in sourcecombine.BUILTIN_PRESETS
        assert sourcecombine.BUILTIN_PRESETS["custom_yaml"]["flags"] == "--format markdown --line-numbers"
        assert sourcecombine.PRESET_ALIASES.get("custom_yaml") == "custom_yaml"
    finally:
        sourcecombine.BUILTIN_PRESETS.clear()
        sourcecombine.BUILTIN_PRESETS.update(orig_builtin)
        sourcecombine.PRESET_ALIASES.clear()
        sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_stdin(monkeypatch):
    preset_data = {
        "custom_stdin": "--format xml --compact"
    }
    stdin_content = json.dumps(preset_data)

    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_content))

    orig_builtin = sourcecombine.BUILTIN_PRESETS.copy()
    orig_aliases = sourcecombine.PRESET_ALIASES.copy()

    try:
        sourcecombine.import_presets("-")
        assert "custom_stdin" in sourcecombine.BUILTIN_PRESETS
        assert sourcecombine.BUILTIN_PRESETS["custom_stdin"]["flags"] == "--format xml --compact"
        assert sourcecombine.BUILTIN_PRESETS["custom_stdin"]["flag"] == "--custom_stdin"
    finally:
        sourcecombine.BUILTIN_PRESETS.clear()
        sourcecombine.BUILTIN_PRESETS.update(orig_builtin)
        sourcecombine.PRESET_ALIASES.clear()
        sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_missing_file(caplog):
    caplog.set_level(logging.ERROR)
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets("non_existent_preset_file.json")
    assert exc_info.value.code == 1
    assert "Presets import file not found" in caplog.text


def test_import_presets_empty_file(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("   \n ", encoding="utf-8")

    res = sourcecombine.import_presets(empty_file)
    assert "is empty; no presets imported" in caplog.text
    assert res == sourcecombine.BUILTIN_PRESETS


def test_import_presets_invalid_json(tmp_path, caplog):
    caplog.set_level(logging.ERROR)
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{invalid_json: 123", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(invalid_file)
    assert exc_info.value.code == 1
    assert "Could not parse presets import file" in caplog.text


def test_import_presets_non_dict_json(tmp_path, caplog):
    caplog.set_level(logging.ERROR)
    file_path = tmp_path / "array.json"
    file_path.write_text('["not", "a", "dict"]', encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(file_path)
    assert exc_info.value.code == 1
    assert "Invalid presets data" in caplog.text


def test_import_presets_list_presets_and_export_presets_integration(tmp_path, capsys):
    preset_data = {
        "custom_test": {
            "flag": "--custom-test",
            "flags": "--format markdown",
            "description": "Integration preset test."
        }
    }
    file_path = tmp_path / "presets.json"
    file_path.write_text(json.dumps(preset_data), encoding="utf-8")

    orig_builtin = sourcecombine.BUILTIN_PRESETS.copy()
    orig_aliases = sourcecombine.PRESET_ALIASES.copy()

    try:
        sourcecombine.import_presets(file_path)
        sourcecombine.print_presets(query="custom_test")
        captured = capsys.readouterr().out
        assert "custom_test" in captured
        assert "--format markdown" in captured

        export_target = tmp_path / "exported.json"
        sourcecombine.export_presets(export_target)
        exported_content = json.loads(export_target.read_text(encoding="utf-8"))
        assert "custom_test" in exported_content["presets"]
    finally:
        sourcecombine.BUILTIN_PRESETS.clear()
        sourcecombine.BUILTIN_PRESETS.update(orig_builtin)
        sourcecombine.PRESET_ALIASES.clear()
        sourcecombine.PRESET_ALIASES.update(orig_aliases)
