import json
import pytest
from unittest.mock import patch, MagicMock
import sourcecombine
from sourcecombine import import_presets, BUILTIN_PRESETS, PRESET_ALIASES, main


@pytest.fixture(autouse=True)
def restore_presets():
    orig_builtin = sourcecombine.BUILTIN_PRESETS.copy()
    orig_aliases = sourcecombine.PRESET_ALIASES.copy()
    yield
    sourcecombine.BUILTIN_PRESETS.clear()
    sourcecombine.BUILTIN_PRESETS.update(orig_builtin)
    sourcecombine.PRESET_ALIASES.clear()
    sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_none_source():
    orig_presets = BUILTIN_PRESETS.copy()
    res = import_presets(None)
    assert res == orig_presets


def test_import_presets_json_file(tmp_path):
    preset_data = {
        "presets": {
            "custom1": {
                "flag": "--custom1",
                "flags": "--format json --compact",
                "description": "Custom preset 1",
                "aliases": ["c1"]
            }
        }
    }
    preset_file = tmp_path / "custom_presets.json"
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    res = import_presets(preset_file)
    assert "custom1" in res
    assert res["custom1"]["description"] == "Custom preset 1"
    assert PRESET_ALIASES.get("custom1") == "custom1"
    assert PRESET_ALIASES.get("c1") == "custom1"


def test_import_presets_yaml_file(tmp_path):
    pytest.importorskip("yaml")
    yaml_content = """
custom_yaml:
  flag: "--custom-yaml"
  flags: "--format markdown --line-numbers"
  description: "Custom YAML preset"
"""
    preset_file = tmp_path / "custom_presets.yml"
    preset_file.write_text(yaml_content, encoding="utf-8")

    res = import_presets(preset_file)
    assert "custom_yaml" in res
    assert res["custom_yaml"]["description"] == "Custom YAML preset"


def test_import_presets_stdin(monkeypatch):
    preset_json = json.dumps({
        "stdin_preset": {
            "flag": "--stdin-preset",
            "flags": "--tree",
            "description": "Stdin preset"
        }
    })
    monkeypatch.setattr("sys.stdin", MagicMock(read=MagicMock(return_value=preset_json)))

    res = import_presets("-")
    assert "stdin_preset" in res
    assert res["stdin_preset"]["description"] == "Stdin preset"


def test_import_presets_empty_file(tmp_path):
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")

    res = import_presets(empty_file)
    assert isinstance(res, dict)


def test_import_presets_nonexistent_file():
    with pytest.raises(SystemExit):
        import_presets("non_existent_preset_file.json")


def test_import_presets_invalid_format(tmp_path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(SystemExit):
        import_presets(invalid_file)


def test_import_presets_os_error(tmp_path):
    p = tmp_path / "unreadable.json"
    p.touch()
    with patch("builtins.open", side_effect=OSError("Read error")):
        with pytest.raises(SystemExit):
            import_presets(p)


def test_import_presets_no_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(sourcecombine.utils, "yaml", None)
    invalid_json = tmp_path / "bad.json"
    invalid_json.write_text("invalid json content", encoding="utf-8")

    with pytest.raises(SystemExit):
        import_presets(invalid_json)


def test_cli_import_presets(tmp_path, capsys):
    preset_data = {
        "cli_preset": {
            "flag": "--cli-preset",
            "flags": "--no-content",
            "description": "CLI test preset"
        }
    }
    preset_file = tmp_path / "cli_presets.json"
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    test_args = ["sourcecombine.py", "--import-presets", str(preset_file), "--list-presets"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "cli_preset" in captured.out
