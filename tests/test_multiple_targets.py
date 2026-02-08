import sys
import os
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch
from sourcecombine import main

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

def test_multiple_folders_as_targets(temp_cwd, mock_argv):
    """Test passing multiple folders as positional arguments."""
    folder1 = temp_cwd / "f1"
    folder1.mkdir()
    (folder1 / "a.py").write_text("a", encoding="utf-8")

    folder2 = temp_cwd / "f2"
    folder2.mkdir()
    (folder2 / "b.py").write_text("b", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 0, 'files_by_extension': {}}

        # Pass both folders as targets
        args = [str(folder1), str(folder2)]
        with mock_argv(args):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        roots = config_passed['search']['root_folders']
        assert str(folder1) in roots
        assert str(folder2) in roots
        assert len(roots) == 2

def test_mixed_folder_and_file_targets(temp_cwd, mock_argv):
    """Test passing a mix of folders and individual files."""
    folder = temp_cwd / "src"
    folder.mkdir()
    (folder / "lib.py").write_text("lib", encoding="utf-8")

    standalone_file = temp_cwd / "main.py"
    standalone_file.write_text("main", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 0, 'files_by_extension': {}}

        args = [str(folder), str(standalone_file)]
        with mock_argv(args):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        roots = config_passed['search']['root_folders']
        assert str(folder) in roots
        assert str(standalone_file) in roots

def test_config_file_plus_additional_targets(temp_cwd, mock_argv):
    """Test passing a config file followed by additional target folders."""
    config_file = temp_cwd / "myconfig.yml"
    config_data = {
        'search': {'root_folders': ['should_be_overridden']},
        'output': {'file': 'combined.txt'}
    }
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    folder = temp_cwd / "real_folder"
    folder.mkdir()
    (folder / "file.txt").write_text("hello", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 0, 'files_by_extension': {}}

        # Config file first, then the folder override
        args = [str(config_file), str(folder)]
        with mock_argv(args):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        roots = config_passed['search']['root_folders']

        # The CLI target 'folder' should override the 'should_be_overridden' in config
        assert str(folder) in roots
        assert 'should_be_overridden' not in roots
        assert len(roots) == 1

        # Ensure other config settings were preserved
        assert config_passed['output']['file'] == 'combined.txt'

def test_individual_file_target(temp_cwd, mock_argv):
    """Test passing a single file as the target."""
    file = temp_cwd / "only_me.txt"
    file.write_text("content", encoding="utf-8")

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 0, 'files_by_extension': {}}

        args = [str(file)]
        with mock_argv(args):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        assert str(file) in config_passed['search']['root_folders']

def test_no_targets_auto_discovery(temp_cwd, mock_argv):
    """Test auto-discovery when no targets are provided."""
    config_file = temp_cwd / "sourcecombine.yml"
    yaml.dump({'search': {'root_folders': ['auto']}}, open(config_file, 'w'))

    with patch('sourcecombine.find_and_combine_files') as mock_combine:
        mock_combine.return_value = {'total_files': 0, 'files_by_extension': {}}

        with mock_argv([]):
            main()

        assert mock_combine.called
        config_passed = mock_combine.call_args[0][0]
        assert config_passed['search']['root_folders'] == ['auto']
