import io
import json
import pytest
import sys
from unittest.mock import patch
import utils
import sourcecombine


@pytest.fixture(autouse=True)
def restore_builtin_presets():
    orig_presets = sourcecombine.copy.deepcopy(sourcecombine.BUILTIN_PRESETS)
    orig_aliases = sourcecombine.copy.deepcopy(sourcecombine.PRESET_ALIASES)
    yield
    sourcecombine.BUILTIN_PRESETS.clear()
    sourcecombine.BUILTIN_PRESETS.update(orig_presets)
    sourcecombine.PRESET_ALIASES.clear()
    sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_none_or_empty():
    assert sourcecombine.import_presets(None) == sourcecombine.BUILTIN_PRESETS
    assert sourcecombine.import_presets("") == sourcecombine.BUILTIN_PRESETS


def test_import_presets_json_file(tmp_path):
    preset_file = tmp_path / "custom_presets.json"
    preset_data = {
        "presets": {
            "test_custom": {
                "flag": "--test-custom",
                "flags": "--format markdown --line-numbers",
                "description": "Test custom preset description"
            }
        }
    }
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    presets = sourcecombine.import_presets(preset_file)
    assert "test_custom" in presets
    assert presets["test_custom"]["flags"] == "--format markdown --line-numbers"
    assert presets["test_custom"]["description"] == "Test custom preset description"


def test_import_presets_yaml_file(tmp_path):
    preset_file = tmp_path / "custom_presets.yml"
    yaml_content = """
my_yaml_preset:
  flags: "--toc --include-tree"
  description: "YAML preset description"
"""
    preset_file.write_text(yaml_content, encoding="utf-8")

    presets = sourcecombine.import_presets(preset_file)
    assert "my_yaml_preset" in presets
    assert presets["my_yaml_preset"]["flags"] == "--toc --include-tree"


def test_import_presets_list_format(tmp_path):
    preset_file = tmp_path / "list_presets.json"
    list_data = [
        {
            "name": "list_preset",
            "flags": "--compact",
            "description": "Preset from list format"
        }
    ]
    preset_file.write_text(json.dumps(list_data), encoding="utf-8")

    presets = sourcecombine.import_presets(preset_file)
    assert "list_preset" in presets
    assert presets["list_preset"]["flags"] == "--compact"


def test_import_presets_stdin(monkeypatch):
    preset_data = {
        "stdin_preset": {
            "flags": "--dry-run",
            "description": "Preset loaded from stdin"
        }
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(preset_data)))

    presets = sourcecombine.import_presets("-")
    assert "stdin_preset" in presets
    assert presets["stdin_preset"]["flags"] == "--dry-run"


def test_import_presets_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("   \n", encoding="utf-8")

    with caplog.at_level("WARNING"):
        presets = sourcecombine.import_presets(empty_file)

    assert "empty" in caplog.text


def test_import_presets_nonexistent_file(tmp_path):
    non_file = tmp_path / "does_not_exist.json"

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(non_file)
    assert exc_info.value.code == 1


def test_import_presets_os_error(tmp_path, monkeypatch):
    test_file = tmp_path / "unreadable.json"
    test_file.write_text("{}", encoding="utf-8")

    def mock_open(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr("builtins.open", mock_open)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(test_file)
    assert exc_info.value.code == 1


def test_import_presets_invalid_format(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text('"just a string"', encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(invalid_file)
    assert exc_info.value.code == 1


def test_import_presets_invalid_syntax(tmp_path):
    syntax_err_file = tmp_path / "syntax.json"
    syntax_err_file.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(syntax_err_file)
    assert exc_info.value.code == 1


def test_import_presets_no_yaml(tmp_path, monkeypatch):
    syntax_err_file = tmp_path / "syntax.json"
    syntax_err_file.write_text("{invalid json", encoding="utf-8")

    monkeypatch.setattr(utils, "yaml", None)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.import_presets(syntax_err_file)
    assert exc_info.value.code == 1


def test_main_import_presets_cli_flag(tmp_path, monkeypatch):
    preset_file = tmp_path / "cli_preset.json"
    preset_file.write_text(json.dumps({
        "cli_custom": {
            "flags": "--show-config",
            "description": "Custom CLI preset"
        }
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        str(tmp_path),
        "--import-presets", str(preset_file),
        "--preset", "cli_custom",
        "--json"
    ])

    captured_out = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured_out)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert captured_out.getvalue().strip().startswith("{")


def test_import_presets_aliases(tmp_path, monkeypatch):
    preset_file = tmp_path / "alias_preset.json"
    preset_file.write_text(json.dumps({
        "alias_custom": {
            "flags": "--show-config",
            "description": "Alias CLI preset"
        }
    }), encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        str(tmp_path),
        "--import-pre", str(preset_file),
        "--preset", "alias_custom",
        "--json"
    ])

    captured_out = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured_out)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0


def test_import_presets_files_from_conflict(tmp_path, monkeypatch):
    preset_file = tmp_path / "preset.json"
    preset_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("sys.argv", [
        "sourcecombine.py",
        "--import-presets", str(preset_file),
        "--files-from", "file_list.txt"
    ])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 1


def test_import_presets_invalid_and_empty_names(tmp_path, monkeypatch):
    preset_file = tmp_path / "invalid_names.json"
    preset_file.write_text("{}", encoding="utf-8")

    preset_data = {
        None: {"flags": "--toc"},
        123: {"flags": "--quiet"},
        "": {"flags": "--compact"},
        "   ": {"flags": "--dry-run"},
        "valid_preset_key": {"flags": "--line-numbers"}
    }
    monkeypatch.setattr(sourcecombine.json, "loads", lambda content: preset_data)

    presets = sourcecombine.import_presets(preset_file)
    assert "valid_preset_key" in presets
    assert None not in presets
    assert 123 not in presets
    assert "" not in presets
    assert "   " not in presets
