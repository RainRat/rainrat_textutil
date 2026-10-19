import json
import logging
from pathlib import Path
import pytest
import sourcecombine


@pytest.fixture(autouse=True)
def restore_builtin_presets():
    orig_presets = dict(sourcecombine.BUILTIN_PRESETS)
    orig_aliases = dict(sourcecombine.PRESET_ALIASES)
    yield
    sourcecombine.BUILTIN_PRESETS.clear()
    sourcecombine.BUILTIN_PRESETS.update(orig_presets)
    sourcecombine.PRESET_ALIASES.clear()
    sourcecombine.PRESET_ALIASES.update(orig_aliases)


def test_import_presets_json_file(tmp_path, monkeypatch):
    preset_data = {
        "presets": {
            "custom1": {
                "flag": "--custom1",
                "flags": "--format markdown --line-numbers",
                "description": "Custom preset 1"
            }
        }
    }
    preset_file = tmp_path / "custom_presets.json"
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    sourcecombine.import_presets(preset_file)

    assert "custom1" in sourcecombine.BUILTIN_PRESETS
    assert sourcecombine.BUILTIN_PRESETS["custom1"]["description"] == "Custom preset 1"
    assert sourcecombine.PRESET_ALIASES.get("custom1") == "custom1"
    assert sourcecombine.PRESET_ALIASES.get("--custom1") == "custom1"


def test_import_presets_yaml_file(tmp_path):
    yaml_content = """
presets:
  custom_yaml:
    flag: "--custom-yaml"
    flags: "--toc --overview"
    description: "Custom YAML preset"
"""
    preset_file = tmp_path / "custom_presets.yml"
    preset_file.write_text(yaml_content, encoding="utf-8")

    sourcecombine.import_presets(preset_file)

    assert "custom_yaml" in sourcecombine.BUILTIN_PRESETS
    assert sourcecombine.BUILTIN_PRESETS["custom_yaml"]["flags"] == "--toc --overview"


def test_import_presets_stdin(monkeypatch):
    preset_data = {
        "my_stdin_preset": {
            "flag": "--stdin-p",
            "flags": "--tree",
            "description": "Stdin preset"
        }
    }
    monkeypatch.setattr("sys.stdin", sourcecombine.io.StringIO(json.dumps(preset_data)))

    sourcecombine.import_presets("-")

    assert "my_stdin_preset" in sourcecombine.BUILTIN_PRESETS


def test_import_presets_cli_execution(tmp_path, monkeypatch, capsys):
    preset_data = {
        "my_cli_preset": {
            "flag": "--my-cli",
            "flags": "--format json --line-numbers",
            "description": "CLI preset test"
        }
    }
    preset_file = tmp_path / "cli_presets.json"
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    test_args = ["sourcecombine.py", "--import-presets", str(preset_file), "--list-presets", "--json"]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    output_json = json.loads(captured.out)
    assert "my_cli_preset" in output_json["presets"]


def test_import_presets_apply_custom_preset(tmp_path, monkeypatch):
    # Create target dummy file
    (tmp_path / "sample.py").write_text("print('hello')", encoding="utf-8")

    preset_data = {
        "fast": {
            "flag": "--fast",
            "flags": "--dry-run --estimate-tokens",
            "description": "Fast analysis"
        }
    }
    preset_file = tmp_path / "presets.json"
    preset_file.write_text(json.dumps(preset_data), encoding="utf-8")

    test_args = ["sourcecombine.py", "--import-presets", str(preset_file), "--preset", "fast", str(tmp_path)]
    monkeypatch.setattr("sys.argv", test_args)

    # Mock find_and_combine_files to check passed config / flags
    called = []
    def mock_combine(config, *args, **kwargs):
        called.append(kwargs)
        return {"total_files": 1}

    monkeypatch.setattr(sourcecombine, "find_and_combine_files", mock_combine)

    sourcecombine.main()

    assert len(called) == 1
    assert called[0]["dry_run"] is True
    assert called[0]["estimate_tokens"] is True


def test_import_presets_empty_file(tmp_path, caplog):
    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        sourcecombine.import_presets(empty_file)

    assert "empty; no presets imported" in caplog.text


def test_import_presets_missing_file():
    with pytest.raises(SystemExit):
        sourcecombine.import_presets("non_existent_presets_file.json")
