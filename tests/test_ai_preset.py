import sys
import os
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine

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

@pytest.fixture
def base_namespace():
    return argparse.Namespace(
        targets=[],
        ai=True,
        markdown=False,
        json=False,
        xml=False,
        format=None,
        line_numbers=False,
        toc=False,
        include_tree=False,
        output=None,
        clipboard=False,
        dry_run=False,
        list_files=False,
        tree=False,
        estimate_tokens=False,
        verbose=False,
        exclude_file=[],
        exclude_folder=[],
        include=[],
        since=None,
        until=None,
        limit=None,
        max_tokens=None,
        files_from=None,
        compact=False,
        sort=None,
        reverse=False,
        extract=False,
        system_info=False,
        init=False,
        restore=False,
        delete_backups=False,
        grep=None,
        exclude_grep=None,
        max_depth=None,
        git_files=False,
        staged=False,
        unstaged=False,
        min_size=None,
        max_size=None,
        max_total_size=None,
        max_total_lines=None,
        min_tokens=None,
        max_file_tokens=None,
        min_lines=None,
        max_file_lines=None,
        config=None,
        apply_in_place=False,
        create_backups=False,
        show_config=False,
        max_lines=None,
        skip_binary=False,
        keep_line_numbers=False,
        overview=False,
        truncate_tokens=None,
        json_summary=None,
        language=[],
        exclude_language=[],
        git_diff=False,
        list_languages=False,
        list_placeholders=False,
        diff=False,
        replace=[],
        replace_line=[],
        map_lang=[],
        pair=[],
        include_unpaired=False,
        pair_template=None,
        unique=False,
        git_log=None,
        verify=False,
        repair=False,
        clean=False,
        preview=False,
        header=None,
        footer=None,
        global_header=None,
        global_footer=None,
        max_size_placeholder=None,
        export_config=None,
        project_info=False,
    )

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_expansion(mock_find_spec, mock_parse_args, base_namespace):
    mock_parse_args.return_value = base_namespace
    mock_find_spec.return_value = MagicMock()

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert base_namespace.markdown is True
        assert base_namespace.line_numbers is True
        assert base_namespace.toc is True
        assert base_namespace.include_tree is True
        assert base_namespace.overview is True
        assert base_namespace.skip_binary is True
        assert base_namespace.unique is True
        assert base_namespace.git_log == 5
        assert base_namespace.include_diff is True
        assert base_namespace.clipboard is True

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_no_clipboard_if_output_provided(mock_find_spec, mock_parse_args, base_namespace):
    base_namespace.output = 'out.txt'
    mock_parse_args.return_value = base_namespace
    mock_find_spec.return_value = MagicMock()

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert base_namespace.markdown is True
        assert base_namespace.clipboard is False

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_no_clipboard_if_no_pyperclip(mock_find_spec, mock_parse_args, base_namespace):
    mock_parse_args.return_value = base_namespace
    mock_find_spec.return_value = None

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert base_namespace.markdown is True
        assert base_namespace.clipboard is False

def test_ai_preset_pyperclip_missing_warning(temp_cwd, mock_argv, caplog):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        sourcecombine.main()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]

        expected_warning = (
            "We could not find the 'pyperclip' library. The AI preset cannot automatically "
            "copy to the clipboard. We will save the output to a file instead. "
            "To copy to the clipboard, please install the library first: pip install pyperclip"
        )
        assert expected_warning in warning_messages

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_respects_explicit_git_log(mock_find_spec, mock_parse_args, base_namespace):
    base_namespace.git_log = 10
    mock_parse_args.return_value = base_namespace
    mock_find_spec.return_value = None

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert base_namespace.git_log == 10
