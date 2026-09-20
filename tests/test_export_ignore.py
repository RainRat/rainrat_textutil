import copy
import json
from pathlib import Path
import pytest
import utils
import sourcecombine
from sourcecombine import export_ignore_patterns


def test_export_ignore_default_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.log', '*.tmp']
    config['filters']['exclusions']['folders'] = ['build/', 'dist/']

    target_file = tmp_path / ".sourcecombineignore"
    export_ignore_patterns(str(target_file), json_format=False, config=config)

    assert target_file.exists()
    content = target_file.read_text(encoding='utf-8')
    assert "# .sourcecombineignore" in content
    assert "# Active ignore patterns exported by SourceCombine" in content
    assert "*.log" in content
    assert "build/" in content


def test_export_ignore_custom_path(tmp_path):
    target_file = tmp_path / "custom" / "my_ignore.txt"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.bak']

    export_ignore_patterns(str(target_file), json_format=False, config=config)

    assert target_file.exists()
    content = target_file.read_text(encoding='utf-8')
    assert "*.bak" in content


def test_export_ignore_directory_target(tmp_path):
    target_dir = tmp_path / "my_dir"
    target_dir.mkdir()
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['folders'] = ['node_modules/']

    export_ignore_patterns(str(target_dir), json_format=False, config=config)

    expected_file = target_dir / ".sourcecombineignore"
    assert expected_file.exists()
    content = expected_file.read_text(encoding='utf-8')
    assert "node_modules/" in content


def test_export_ignore_stdout(capsys):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.o']

    export_ignore_patterns("-", json_format=False, config=config)

    captured = capsys.readouterr()
    assert "# Active ignore patterns exported by SourceCombine" in captured.out
    assert "*.o" in captured.out


def test_export_ignore_json_format(capsys):
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['filters']['exclusions']['filenames'] = ['*.pyc']
    config['filters']['exclusions']['folders'] = ['__pycache__/']

    export_ignore_patterns("-", json_format=True, config=config)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "ignore_patterns" in data
    assert data["total"] > 0
    assert "*.pyc" in data["ignore_patterns"]["Excluded Filenames (Config)"]


def test_export_ignore_dry_run(tmp_path):
    target_file = tmp_path / "should_not_exist.txt"
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    export_ignore_patterns(str(target_file), json_format=False, config=config, dry_run=True)

    assert not target_file.exists()


def test_export_ignore_cli_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--export-ignore"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    exported_file = tmp_path / ".sourcecombineignore"
    assert exported_file.exists()


def test_export_ignore_cli_alias_stdout_json(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--export-ig", "-", "--json"])

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "ignore_patterns" in data
