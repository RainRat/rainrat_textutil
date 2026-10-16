import copy
import json
import pytest
from unittest.mock import patch
import utils
import sourcecombine
from sourcecombine import import_presets, export_presets, BUILTIN_PRESETS, PRESET_ALIASES, main


@pytest.fixture(autouse=True)
def restore_presets():
    """Backup and restore BUILTIN_PRESETS and PRESET_ALIASES before and after each test."""
    orig_presets = copy.deepcopy(BUILTIN_PRESETS)
    orig_aliases = copy.deepcopy(PRESET_ALIASES)
    yield
    BUILTIN_PRESETS.clear()
    BUILTIN_PRESETS.update(orig_presets)
    PRESET_ALIASES.clear()
    PRESET_ALIASES.update(orig_aliases)


def test_import_presets_round_trip(tmp_path):
    """Test round-trip export and import of preset definitions."""
    export_file = tmp_path / "exported_presets.json"
    export_presets(export_file)
    assert export_file.exists()

    presets = import_presets(export_file)
    assert "ai" in presets
    assert "analyze" in presets
    assert "review" in presets


def test_import_presets_dict_format(tmp_path):
    """Test importing presets from a JSON dictionary structure."""
    preset_file = tmp_path / "custom_presets.json"
    data = {
        "presets": {
            "test_preset_a": {
                "flag": "--test-a",
                "flags": "--format markdown --line-numbers",
                "description": "Test Preset A"
            }
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    presets = import_presets(preset_file)
    assert "test_preset_a" in presets
    assert presets["test_preset_a"]["flag"] == "--test-a"
    assert presets["test_preset_a"]["flags"] == "--format markdown --line-numbers"
    assert presets["test_preset_a"]["description"] == "Test Preset A"


def test_import_presets_direct_dict_format(tmp_path):
    """Test importing presets from a direct key-value dictionary."""
    preset_file = tmp_path / "direct_presets.json"
    data = {
        "test_preset_b": {
            "flags": "--format json --compact",
            "description": "Direct Preset B"
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    presets = import_presets(preset_file)
    assert "test_preset_b" in presets
    assert presets["test_preset_b"]["flags"] == "--format json --compact"
    assert presets["test_preset_b"]["flag"] == "--preset test_preset_b"


def test_import_presets_array_format(tmp_path):
    """Test importing presets from a JSON array."""
    preset_file = tmp_path / "array_presets.json"
    data = [
        {
            "name": "test_preset_c",
            "flag": "--test-c",
            "flags": ["--format", "csv", "--compact"],
            "description": "Array Preset C"
        }
    ]
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    presets = import_presets(preset_file)
    assert "test_preset_c" in presets
    assert presets["test_preset_c"]["flags"] == "--format csv --compact"


def test_import_presets_yaml_format(tmp_path):
    """Test importing presets from a YAML file."""
    if not utils.yaml:
        pytest.skip("PyYAML not installed")

    yaml_file = tmp_path / "presets.yml"
    yaml_content = """
presets:
  test_preset_yaml:
    flag: "--test-yaml"
    flags: "--format text --line-numbers"
    description: "YAML Preset"
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    presets = import_presets(yaml_file)
    assert "test_preset_yaml" in presets
    assert presets["test_preset_yaml"]["flags"] == "--format text --line-numbers"


def test_import_presets_stdin(monkeypatch):
    """Test importing presets from standard input ('-')."""
    data = {
        "presets": {
            "stdin_preset": {
                "flags": "--format xml",
                "description": "Stdin Preset"
            }
        }
    }
    json_str = json.dumps(data)
    monkeypatch.setattr("sys.stdin", pytest.importorskip("io").StringIO(json_str))

    presets = import_presets("-")
    assert "stdin_preset" in presets
    assert presets["stdin_preset"]["flags"] == "--format xml"


def test_import_presets_missing_file(tmp_path):
    """Test error handling when the preset import file is missing."""
    missing_file = tmp_path / "nonexistent.json"
    with pytest.raises(SystemExit) as exc_info:
        import_presets(missing_file)
    assert exc_info.value.code == 1


def test_import_presets_invalid_syntax(tmp_path):
    """Test error handling when the preset file contains invalid syntax."""
    bad_file = tmp_path / "invalid_syntax.json"
    bad_file.write_text("{ bad json or yaml content", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        import_presets(bad_file)
    assert exc_info.value.code == 1


def test_import_presets_invalid_structure(tmp_path):
    """Test error handling when preset import file contains non-dict non-list JSON."""
    invalid_file = tmp_path / "number.json"
    invalid_file.write_text("12345", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        import_presets(invalid_file)
    assert exc_info.value.code == 1


def test_import_presets_empty_file_and_none(tmp_path):
    """Test handling of empty path, None, and empty files."""
    assert import_presets(None) is BUILTIN_PRESETS
    assert import_presets("") is BUILTIN_PRESETS

    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    assert import_presets(empty_file) is BUILTIN_PRESETS


def test_cli_import_presets_and_list(tmp_path, capsys):
    """Test CLI execution combining --import-presets with --list-presets."""
    preset_file = tmp_path / "presets.json"
    data = {
        "presets": {
            "cli_test_preset": {
                "flag": "--cli-preset",
                "flags": "--format markdown --line-numbers",
                "description": "CLI Test Preset"
            }
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    test_args = ["sourcecombine.py", "--import-presets", str(preset_file), "--list-presets"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "cli_test_preset" in captured.out
    assert "--cli-preset" in captured.out


def test_cli_import_presets_and_use_preset(tmp_path):
    """Test CLI execution importing a custom preset and invoking it with --preset."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").write_text("print('hello')", encoding="utf-8")

    preset_file = tmp_path / "presets.json"
    out_file = tmp_path / "output.md"
    data = {
        "custom_md": {
            "flags": f"--format markdown --output {out_file}",
            "description": "Custom Markdown Export"
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    test_args = [
        "sourcecombine.py",
        str(src_dir),
        "--import-presets",
        str(preset_file),
        "--preset",
        "custom_md"
    ]
    with patch("sys.argv", test_args):
        main()

    assert out_file.exists()
    assert "```python" in out_file.read_text(encoding="utf-8")


def test_cli_import_preset_aliases(tmp_path, capsys):
    """Test CLI execution using --import-pre and --import-preset aliases."""
    preset_file = tmp_path / "presets.json"
    data = {
        "alias_preset": {
            "flags": "--compact",
            "description": "Alias Preset"
        }
    }
    preset_file.write_text(json.dumps(data), encoding="utf-8")

    test_args = ["sourcecombine.py", "--import-pre", str(preset_file), "--list-presets"]
    with patch("sys.argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "alias_preset" in captured.out
