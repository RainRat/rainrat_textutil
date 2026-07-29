import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sys
import os
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml

# Adjust sys.path to include the project root

from sourcecombine import main

@pytest.fixture
def temp_cwd(tmp_path):
    """Context manager to change current working directory."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_argv():
    """Context manager to mock sys.argv."""
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

def test_smart_extension_markdown(temp_cwd, mock_argv):
    """Verify -m produces combined_files.md."""
    with mock_argv(['.','-m', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            # Check the second argument to find_and_combine_files (output_path)
            args, _ = mock_combine.call_args
            assert args[1] == 'combined_files.md'
            # Also check if config was updated
            assert args[0]['output']['file'] == 'combined_files.md'

def test_smart_extension_json(temp_cwd, mock_argv):
    """Verify -j produces combined_files.json."""
    with mock_argv(['.','-j', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            assert args[1] == 'combined_files.json'
            assert args[0]['output']['file'] == 'combined_files.json'

def test_smart_extension_xml(temp_cwd, mock_argv):
    """Verify -f xml produces combined_files.xml."""
    with mock_argv(['.','-f', 'xml', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            assert args[1] == 'combined_files.xml'
            assert args[0]['output']['file'] == 'combined_files.xml'

def test_config_format_respect(temp_cwd, mock_argv):
    """Verify format: json in config is respected and produces .json."""
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'output': {'format': 'json'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with mock_argv(['--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, kwargs = mock_combine.call_args
            assert args[1] == 'combined_files.json'
            assert kwargs['output_format'] == 'json'

def test_explicit_output_preserved(temp_cwd, mock_argv):
    """Verify explicit -o my.txt is NOT changed even for markdown."""
    with mock_argv(['.','-m', '-o', 'my.txt', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            assert args[1] == 'my.txt'

def test_cli_override_config_format(temp_cwd, mock_argv):
    """Verify CLI -f text overrides config format: markdown."""
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'search': {'root_folders': ['.']},
        'output': {'format': 'markdown'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    with mock_argv(['-f', 'text', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, kwargs = mock_combine.call_args
            assert args[1] == 'combined_files.txt'
            assert kwargs['output_format'] == 'text'

def test_trailing_slash_output(temp_cwd, mock_argv):
    """Verify that a trailing slash in output path treats it as a directory."""
    # Note: Use a path that doesn't exist yet to verify it works for new dirs too.
    output_dir = "new_output_dir/"
    with mock_argv(['.', '-o', output_dir, '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            # It should have appended the default filename
            expected_path = os.path.join("new_output_dir", "combined_files.txt")
            assert args[1] == expected_path

def test_trailing_slash_with_format(temp_cwd, mock_argv):
    """Verify trailing slash with format shortcut works together."""
    output_dir = "markdown_dir/"
    with mock_argv(['.', '-o', output_dir, '-m', '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            args, _ = mock_combine.call_args
            expected_path = os.path.join("markdown_dir", "combined_files.md")
            assert args[1] == expected_path

def test_init_workflow_succeeds_out_of_the_box(temp_cwd, mock_argv, caplog):
    """Verify that after running --init, running the tool succeeds out-of-the-box."""
    with mock_argv(['--init']):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0

    assert (temp_cwd / "sourcecombine.yml").exists()

    dummy_file = temp_cwd / "dummy.txt"
    dummy_file.write_text("Hello World", encoding="utf-8")

    caplog.clear()
    with mock_argv(['--dry-run']):
        main()

    warning_msgs = [record.message for record in caplog.records if record.levelname == "WARNING"]
    for msg in warning_msgs:
        assert "/path/to/project" not in msg

def test_config_auto_discovery_with_targets(temp_cwd, mock_argv):
    """Verify that configuration file is auto-discovered even with targets."""
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'output': {'file': 'my_special_combined.txt'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    # We provide a targets list, which would previously skip auto-finding
    target_dir = temp_cwd / "some_src"
    target_dir.mkdir()

    with mock_argv([str(target_dir), '--dry-run']):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {}
            main()

            assert mock_combine.called
            args, _ = mock_combine.call_args
            # The output path should be resolved based on the config file name
            assert os.path.basename(args[1]) == 'my_special_combined.txt'
            # The config passed to find_and_combine_files should have 'my_special_combined.txt'
            assert args[0]['output']['file'] == 'my_special_combined.txt'

def test_project_info_config_auto_discovery_with_targets(temp_cwd, mock_argv):
    """Verify project-info auto-discovers configuration even with targets."""
    config_file = temp_cwd / "sourcecombine.yml"
    config_data = {
        'project': {
            'name': 'MySuperProject',
            'version': '9.9.9'
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    target_dir = temp_cwd / "some_src"
    target_dir.mkdir()

    # We mock _populate_project_stats or print_project_info or get_git_info
    with mock_argv(['--project-info', str(target_dir)]):
        with patch('sourcecombine.print_project_info') as mock_print:
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 0
            assert mock_print.called
            stats = mock_print.call_args[0][0]
            assert stats.get('project_name') == 'MySuperProject'
            assert stats.get('project_version') == '9.9.9'
