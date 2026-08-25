import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main

@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_argv():
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

def test_ai_preset_expansion(temp_cwd, mock_argv):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', return_value=MagicMock()) as mock_find_spec, \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        mock_combine.assert_called_once()
        called_config = mock_combine.call_args[0][0]
        called_kwargs = mock_combine.call_args[1]

        # Verify output formats and preset flags mapped to config
        assert called_kwargs.get('output_format') == 'markdown'
        assert called_kwargs.get('clipboard') is True
        assert called_config['output'].get('add_line_numbers') is True
        assert called_config['output'].get('table_of_contents') is True
        assert called_config['output'].get('include_tree') is True
        assert called_config['output'].get('project_overview') is True
        assert called_config['filters'].get('skip_binary') is True
        assert called_config['filters'].get('unique') is True
        assert called_config['output'].get('include_diff') is True
        assert called_config['output'].get('git_log_count') == 5

def test_ai_preset_no_clipboard_if_output_provided(temp_cwd, mock_argv):
    with mock_argv(['.', '--ai', '--output', 'out.txt']), \
         patch('importlib.util.find_spec', return_value=MagicMock()), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        mock_combine.assert_called_once()
        called_kwargs = mock_combine.call_args[1]
        assert called_kwargs.get('clipboard') is False

def test_ai_preset_no_clipboard_if_no_pyperclip(temp_cwd, mock_argv):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        mock_combine.assert_called_once()
        called_kwargs = mock_combine.call_args[1]
        assert called_kwargs.get('clipboard') is False

def test_ai_preset_pyperclip_missing_warning(temp_cwd, mock_argv, caplog):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]

        expected_warning = (
            "We could not find the 'pyperclip' library. The AI preset cannot automatically "
            "copy to the clipboard. We will save the output to a file instead. "
            "To copy to the clipboard, please install the library first: pip install pyperclip"
        )
        assert expected_warning in warning_messages

def test_ai_preset_respects_explicit_git_log(temp_cwd, mock_argv):
    with mock_argv(['.', '--ai', '--git-log', '10']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        mock_combine.assert_called_once()
        called_config = mock_combine.call_args[0][0]
        assert called_config['output'].get('git_log_count') == 10

def test_ai_preset_respects_explicit_disabled_git_log(temp_cwd, mock_argv):
    with mock_argv(['.', '--ai', '--git-log', '0']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        mock_combine.assert_called_once()
        called_config = mock_combine.call_args[0][0]
        assert called_config['output'].get('git_log_count') == 0

def test_ai_preset_handles_find_spec_exception(temp_cwd, mock_argv):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', side_effect=Exception("Module error")), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        try:
            main()
        except SystemExit:
            pass

        mock_combine.assert_called_once()
        called_kwargs = mock_combine.call_args[1]
        assert called_kwargs.get('clipboard') is False
