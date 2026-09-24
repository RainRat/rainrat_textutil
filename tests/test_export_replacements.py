import json
import pytest
from sourcecombine import export_replacements, main, utils


def test_export_replacements_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = {
        "processing": {
            "regex_replacements": [{"pattern": "foo", "replacement": "bar"}],
            "line_regex_replacements": [{"pattern": "hello", "replacement": "world"}]
        }
    }
    export_replacements(None, config=config)

    target_file = tmp_path / "replacements.json"
    assert target_file.is_file()

    data = json.loads(target_file.read_text(encoding="utf-8"))
    assert data["exported_to"] == str(target_file.resolve())
    assert data["total_rules"] == 2
    assert data["regex_replacements"] == [{"pattern": "foo", "replacement": "bar"}]
    assert data["line_regex_replacements"] == [{"pattern": "hello", "replacement": "world"}]


def test_export_replacements_custom_file(tmp_path):
    target_file = tmp_path / "custom_rules.json"
    config = {
        "processing": {
            "regex_replacements": [{"pattern": "a", "replacement": "b"}]
        }
    }
    export_replacements(str(target_file), config=config)

    assert target_file.is_file()
    data = json.loads(target_file.read_text(encoding="utf-8"))
    assert data["exported_to"] == str(target_file.resolve())
    assert data["total_rules"] == 1


def test_export_replacements_target_dir(tmp_path):
    target_dir = tmp_path / "output_dir"
    target_dir.mkdir()
    config = {
        "processing": {
            "line_regex_replacements": [{"pattern": "x", "replacement": "y"}]
        }
    }
    export_replacements(str(target_dir), config=config)

    expected_file = target_dir / "replacements.json"
    assert expected_file.is_file()
    data = json.loads(expected_file.read_text(encoding="utf-8"))
    assert data["total_rules"] == 1


def test_export_replacements_stdout(capsys):
    config = {
        "processing": {
            "regex_replacements": [{"pattern": "test", "replacement": "pass"}]
        }
    }
    export_replacements("-", config=config)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["total_rules"] == 1
    assert data["regex_replacements"] == [{"pattern": "test", "replacement": "pass"}]


def test_export_replacements_cli(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    test_args = [
        "sourcecombine.py",
        "--replace", "foo", "bar",
        "--replace-line", "baz", "qux",
        "--export-rep", "-"
    ]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["exported_to"] == "-"
    assert data["total_rules"] == 2


def test_export_replacements_cli_files_from_conflict(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    test_args = [
        "sourcecombine.py",
        "--files-from", "-",
        "--export-replacements"
    ]
    monkeypatch.setattr("sys.argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_export_replacements_oserror(tmp_path, monkeypatch):
    invalid_path = tmp_path / "nonexistent_dir" / "file.json"
    config = {"processing": {}}

    # Make directory creation fail
    monkeypatch.setattr("pathlib.Path.mkdir", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("Disk write error")))

    with pytest.raises(SystemExit) as exc_info:
        export_replacements(str(invalid_path), config=config)

    assert exc_info.value.code == 1
