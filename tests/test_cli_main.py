import sys
import os
import shutil
import logging
import runpy
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import yaml

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
from sourcecombine import main, utils

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging before and after each test."""
    # Reset root logger handlers
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.setLevel(logging.NOTSET)

    yield

    # Cleanup again
    for h in root.handlers[:]:
        root.removeHandler(h)

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

def test_init_creates_default_config_from_template(temp_cwd, mock_argv, caplog):
    """Test --init copies the template when it exists."""
    # We rely on the actual config.template.yml being present in the repo
    # sourcecombine.py looks for it relative to itself.

    caplog.set_level(logging.INFO)

    with mock_argv(['--init']):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    assert (temp_cwd / "sourcecombine.yml").exists()
    assert "Created default configuration" in caplog.text

def test_init_fails_if_config_exists(temp_cwd, mock_argv, caplog):
    """Test --init aborts if sourcecombine.yml already exists."""
    (temp_cwd / "sourcecombine.yml").write_text("existing", encoding="utf-8")

    caplog.set_level(logging.ERROR)

    with mock_argv(['--init']):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "already exists" in caplog.text
    assert (temp_cwd / "sourcecombine.yml").read_text(encoding="utf-8") == "existing"

def test_init_creates_minimal_config_if_template_missing(temp_cwd, mock_argv, caplog):
    """Test --init creates minimal config if template is missing."""

    caplog.set_level(logging.INFO)

    fake_script_path = temp_cwd / "fake_script.py"
    fake_script_path.touch()

    with patch('sourcecombine.__file__', str(fake_script_path)):
        with mock_argv(['--init']):
            with pytest.raises(SystemExit) as excinfo:
                main()

    assert excinfo.value.code == 0
    assert (temp_cwd / "sourcecombine.yml").exists()
    assert "Template not found" in caplog.text
    assert "Created a simple configuration" in caplog.text

    # Verify content is minimal default
    content = (temp_cwd / "sourcecombine.yml").read_text(encoding="utf-8")
    assert "# Default SourceCombine Configuration" in content

def test_init_fails_to_write_config(temp_cwd, mock_argv, caplog):
    """Test handling of write permission error during --init minimal config creation."""
    fake_script_path = temp_cwd / "fake_script.py"
    fake_script_path.touch()

    caplog.set_level(logging.ERROR)

    # Simulate template missing to trigger minimal config creation
    with patch('sourcecombine.__file__', str(fake_script_path)):
        # Mock open to raise OSError
        with patch('builtins.open', side_effect=OSError("Permission denied")):
             with mock_argv(['--init']):
                with pytest.raises(SystemExit) as excinfo:
                    main()

    assert excinfo.value.code == 1
    assert "Could not write the configuration file" in caplog.text

def test_auto_finding_success(temp_cwd, mock_argv, caplog):
    """Test that main finds a default config file when none is specified."""
    config_file = temp_cwd / "config.yaml"
    config_data = {
        'search': {'root_folders': ['.']},
        'output': {'file': 'out.txt'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    caplog.set_level(logging.INFO)

    # Mock find_and_combine_files to avoid actual processing
    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        with mock_argv([]):
            main()

    assert "Auto-found config file: config.yaml" in caplog.text
    mock_combine.assert_called_once()

def test_cwd_fallback(temp_cwd, mock_argv, caplog):
    """Test that main falls back to CWD if no config file is found."""
    # Ensure no default files exist

    caplog.set_level(logging.INFO)

    # Mock find_and_combine_files to avoid actual processing
    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        with mock_argv([]):
            main()

    assert "No config file found" in caplog.text
    assert "Scanning current folder '.' with default settings" in caplog.text
    mock_combine.assert_called_once()
    # Verify the config passed has root_folders set to ['.']
    args, _ = mock_combine.call_args
    assert args[0]['search']['root_folders'] == ['.']

def test_explicit_config_not_found(temp_cwd, mock_argv, caplog):
    """Test that main exits if specified config file is missing."""
    caplog.set_level(logging.ERROR)

    with mock_argv(['missing_config.yml']):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "Could not find the configuration file" in caplog.text

def test_invalid_config_structure(temp_cwd, mock_argv, caplog):
    """Test that main exits if config file is invalid."""
    config_file = temp_cwd / "bad.yml"
    config_file.write_text("invalid_yaml: [ unclosed list", encoding="utf-8")

    caplog.set_level(logging.ERROR)

    with mock_argv([str(config_file)]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "The configuration is not valid" in caplog.text

def test_config_missing_root_folders_fallback(temp_cwd, mock_argv, caplog):
    """Test that main defaults to CWD if config file is missing root_folders."""
    config_file = temp_cwd / "incomplete.yml"
    # Missing search.root_folders
    yaml.dump({'output': {'file': 'out.txt'}}, open(config_file, 'w'))

    caplog.set_level(logging.INFO)

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {}
        with mock_argv([str(config_file)]):
            main()

    assert "No root folders specified in configuration" in caplog.text
    assert "Scanning current folder '.'" in caplog.text
    mock_combine.assert_called_once()
    # Verify the config passed has root_folders set to ['.']
    args, _ = mock_combine.call_args
    assert args[0]['search']['root_folders'] == ['.']

def test_main_entry_point():
    """Cover sourcecombine.py line 2385: if __name__ == "__main__": main()."""
    with patch.object(sys, 'argv', ['sourcecombine.py', '--version']):
        with pytest.raises(SystemExit) as excinfo:
            runpy.run_path("sourcecombine.py", run_name="__main__")
        assert excinfo.value.code == 0

def test_line_numbers_flag_in_main_coverage(tmp_path, monkeypatch):
    """Cover sourcecombine.py line 1907: --line-numbers flag in main()."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("content", encoding="utf-8")

    out_file = tmp_path / "out.txt"
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", str(root), "-o", str(out_file), "--line-numbers"])

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "1: content" in content

def test_smart_extension_jsonl(tmp_path, temp_cwd, monkeypatch):
    """Cover sourcecombine.py: --format jsonl produces combined_files.jsonl by default."""
    (tmp_path / "file.txt").write_text("hello")

    # Use a non-default filename by format
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", "--format", "jsonl"])
    try:
        main()
    except SystemExit:
        pass
    # Default filename for jsonl should be combined_files.jsonl
    assert Path("combined_files.jsonl").exists()

def test_main_time_filtering_cli_since(tmp_path, mock_argv):
    out_file = tmp_path / "out.txt"
    with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
        with mock_argv(['.', '-o', str(out_file), '--since', '2024-01-01']):
            main()
            config = mock_combine.call_args[0][0]
            assert config['filters']['modified_since'] == utils.parse_time_value('2024-01-01')

def test_main_time_filtering_cli_until(tmp_path, mock_argv):
    out_file = tmp_path / "out.txt"
    with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
        with mock_argv(['.', '-o', str(out_file), '--until', '1h']):
            main()
            config = mock_combine.call_args[0][0]
            assert config['filters']['modified_until'] == pytest.approx(utils.parse_time_value('1h'), abs=2)

def test_main_time_filtering_cli_error_handling(caplog, mock_argv):
    caplog.set_level(logging.ERROR)
    with mock_argv(['--since', 'invalid']):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "Invalid time value" in caplog.text

def test_main_time_filtering_no_filters_dict(tmp_path, mock_argv):
    out_file = tmp_path / "out.txt"
    with patch('sourcecombine.load_and_validate_config', return_value={'search': {'root_folders': ['.']}, 'output': {}}):
        with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
            with mock_argv(['.', '-o', str(out_file), '--since', '2024-01-01']):
                main()
                config = mock_combine.call_args[0][0]
                assert 'filters' in config
                assert config['filters']['modified_since'] == utils.parse_time_value('2024-01-01')

def test_main_system_info_exit_behavior():
    with patch.object(sys, "argv", ["sourcecombine.py", "--system-info"]):
        with patch("sourcecombine.print_system_info") as mock_info:
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0
            mock_info.assert_called_once()
