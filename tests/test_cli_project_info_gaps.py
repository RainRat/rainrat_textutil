import sys
import os
from pathlib import Path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import sourcecombine
import pytest

def test_main_project_info_config_path_target(tmp_path, monkeypatch, mocker):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    config_file = tmp_path / "custom_config.yml"
    config_file.write_text("search:\n  root_folders: ['.']", encoding='utf-8')

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info', str(config_file)])

    mocker.patch("sourcecombine._populate_project_stats")
    mocker.patch("sourcecombine._get_git_info", return_value={"branch": "main"})
    mocker.patch("sourcecombine.print_project_info")

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code == 0

def test_main_project_info_default_config_discovery(tmp_path, monkeypatch, mocker):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    config_file = project_dir / "sourcecombine.yml"
    config_file.write_text("search:\n  root_folders: ['.']", encoding='utf-8')

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info'])

    mocker.patch("sourcecombine._populate_project_stats")
    mocker.patch("sourcecombine._get_git_info", return_value={})
    mocker.patch("sourcecombine.print_project_info")

    mock_load = mocker.patch("sourcecombine.load_and_validate_config", wraps=sourcecombine.load_and_validate_config)

    with pytest.raises(SystemExit):
        sourcecombine.main()

    args, _ = mock_load.call_args
    assert "sourcecombine.yml" in str(args[0])

def test_main_project_info_invalid_config_handling(tmp_path, monkeypatch, caplog):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    config_file = project_dir / "invalid.yml"
    config_file.write_text("invalid: [", encoding='utf-8')

    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--project-info', '-c', str(config_file)])

    with pytest.raises(SystemExit) as exc:
        sourcecombine.main()
    assert exc.value.code != 0

    assert "Error parsing YAML file" in caplog.text
