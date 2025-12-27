import sys
import os
import shutil
import logging
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
    assert "Created minimal configuration" in caplog.text

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
    assert "Failed to write config" in caplog.text

def test_auto_discovery_success(temp_cwd, mock_argv, caplog):
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

    assert "Auto-discovered config file: config.yaml" in caplog.text
    mock_combine.assert_called_once()

def test_auto_discovery_failure(temp_cwd, mock_argv, caplog):
    """Test that main exits if no config file is specified or found."""
    # Ensure no default files exist

    # We need to capture stderr because parser.error prints to stderr and exits
    # argparse usually calls sys.exit(2) on error

    with mock_argv([]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    # Exit code 2 is standard for argparse errors
    assert excinfo.value.code == 2

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
    assert "Invalid configuration" in caplog.text

def test_invalid_config_validation(temp_cwd, mock_argv, caplog):
    """Test that main exits if config fails validation (e.g. missing required keys)."""
    config_file = temp_cwd / "incomplete.yml"
    # Missing search.root_folders
    yaml.dump({'output': {'file': 'out.txt'}}, open(config_file, 'w'))

    caplog.set_level(logging.ERROR)

    with mock_argv([str(config_file)]):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1
    assert "Invalid configuration" in caplog.text
