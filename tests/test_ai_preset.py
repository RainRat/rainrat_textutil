import sys
import os
import argparse
import logging
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
def mock_main_deps():
    with patch('sourcecombine.load_and_validate_config', return_value={}), \
         patch('sourcecombine.find_and_combine_files', return_value={}), \
         patch('sourcecombine._print_execution_summary'), \
         patch('sys.exit'):
        yield

@pytest.fixture
def capture_parsed_args():
    captured = []
    original_parse_args = argparse.ArgumentParser.parse_args

    def mock_parse_args(self, *args, **kwargs):
        parsed_args = original_parse_args(self, *args, **kwargs)
        captured.append(parsed_args)
        return parsed_args

    with patch('argparse.ArgumentParser.parse_args', mock_parse_args):
        yield captured

def test_ai_preset_expansion(temp_cwd, mock_main_deps, capture_parsed_args):
    with patch('importlib.util.find_spec', return_value=MagicMock()), \
         patch.object(sys, 'argv', ['sourcecombine.py', '.', '--ai']):

        main()

        assert len(capture_parsed_args) == 1
        args = capture_parsed_args[0]
        assert args.markdown is True
        assert args.line_numbers is True
        assert args.toc is True
        assert args.include_tree is True
        assert args.overview is True
        assert args.skip_binary is True
        assert args.unique is True
        assert args.git_log == 5
        assert args.include_diff is True
        assert args.clipboard is True

def test_ai_preset_no_clipboard_if_output_provided(temp_cwd, mock_main_deps, capture_parsed_args):
    with patch('importlib.util.find_spec', return_value=MagicMock()), \
         patch.object(sys, 'argv', ['sourcecombine.py', '.', '--ai', '--output', 'out.txt']):

        main()

        assert len(capture_parsed_args) == 1
        args = capture_parsed_args[0]
        assert args.markdown is True
        assert args.clipboard is False

def test_ai_preset_no_clipboard_if_no_pyperclip(temp_cwd, mock_main_deps, capture_parsed_args):
    with patch('importlib.util.find_spec', return_value=None), \
         patch.object(sys, 'argv', ['sourcecombine.py', '.', '--ai']):

        main()

        assert len(capture_parsed_args) == 1
        args = capture_parsed_args[0]
        assert args.markdown is True
        assert args.clipboard is False

def test_ai_preset_pyperclip_missing_warning(temp_cwd, mock_main_deps, caplog):
    with patch('importlib.util.find_spec', return_value=None), \
         patch.object(sys, 'argv', ['sourcecombine.py', '.', '--ai']):

        main()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]
        expected_warning = (
            "We could not find the 'pyperclip' library. The AI preset cannot automatically "
            "copy to the clipboard. We will save the output to a file instead. "
            "To copy to the clipboard, please install the library first: pip install pyperclip"
        )
        assert expected_warning in warning_messages

def test_ai_preset_respects_explicit_git_log(temp_cwd, mock_main_deps, capture_parsed_args):
    with patch('importlib.util.find_spec', return_value=MagicMock()), \
         patch.object(sys, 'argv', ['sourcecombine.py', '.', '--ai', '--git-log', '10']):

        main()

        assert len(capture_parsed_args) == 1
        args = capture_parsed_args[0]
        assert args.git_log == 10
        assert args.markdown is True
        assert args.clipboard is True

def test_ai_preset_respects_explicit_disabled_git_log(temp_cwd, mock_main_deps, capture_parsed_args):
    with patch('importlib.util.find_spec', return_value=MagicMock()), \
         patch.object(sys, 'argv', ['sourcecombine.py', '.', '--ai', '--git-log', '0']):

        main()

        assert len(capture_parsed_args) == 1
        args = capture_parsed_args[0]
        assert args.git_log == 0
