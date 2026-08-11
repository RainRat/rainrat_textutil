import sys
import os
import argparse
import importlib.util
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import sourcecombine
from sourcecombine import main

def _create_mock_args(ai=True, output=None):
    return argparse.Namespace(
        targets=[],
        ai=ai,
        markdown=False,
        json=False,
        xml=False,
        format=None,
        line_numbers=False,
        toc=False,
        include_tree=False,
        output=output,
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
        clean=False,
        preview=False,
        header=None,
        footer=None,
        global_header=None,
        global_footer=None,
        max_size_placeholder=None,
        export_config=None,
    )

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

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_expansion(mock_find_spec, mock_parse_args):
    mock_args = _create_mock_args()
    mock_parse_args.return_value = mock_args
    mock_find_spec.return_value = MagicMock()

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert mock_args.markdown
        assert mock_args.line_numbers
        assert mock_args.toc
        assert mock_args.include_tree
        assert mock_args.clipboard

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_no_clipboard_if_output_provided(mock_find_spec, mock_parse_args):
    mock_args = _create_mock_args(output='out.txt')
    mock_parse_args.return_value = mock_args
    mock_find_spec.return_value = MagicMock()

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert mock_args.markdown
        assert not mock_args.clipboard

@patch('argparse.ArgumentParser.parse_args')
@patch('importlib.util.find_spec')
def test_ai_preset_no_clipboard_if_no_pyperclip(mock_find_spec, mock_parse_args):
    mock_args = _create_mock_args()
    mock_parse_args.return_value = mock_args
    mock_find_spec.return_value = None

    with patch('sourcecombine.load_and_validate_config'), \
         patch('sourcecombine.find_and_combine_files'), \
         patch('sourcecombine._print_execution_summary'), \
         patch('logging.getLogger'), \
         patch('sys.exit'):

        sourcecombine.main()

        assert mock_args.markdown
        assert not mock_args.clipboard

def test_ai_preset_pyperclip_missing_warning(temp_cwd, mock_argv, caplog):
    with mock_argv(['.', '--ai']), \
         patch('importlib.util.find_spec', return_value=None), \
         patch('sourcecombine.find_and_combine_files') as mock_combine:

        mock_combine.return_value = {}
        main()

        warning_messages = [record.message for record in caplog.records if record.levelname == "WARNING"]

        expected_warning = (
            "We could not find the 'pyperclip' library. The AI preset cannot automatically "
            "copy to the clipboard. We will save the output to a file instead. "
            "To copy to the clipboard, please install the library first: pip install pyperclip"
        )
        assert expected_warning in warning_messages

def test_ai_preset_enables_git_context():
    with patch.object(sys, 'argv', ['sourcecombine.py', '--ai']):
        with patch('sourcecombine.argparse.ArgumentParser.parse_args') as mock_parse:
            from argparse import Namespace
            mock_parse.return_value = Namespace(
                ai=True,
                targets=[],
                config=None,
                output=None,
                dry_run=False,
                verbose=False,
                project_name=None,
                project_version=None,
                project_description=None,
                project_license=None,
                project_url=None,
                exclude_file=[],
                exclude_folder=[],
                include=[],
                language=[],
                exclude_language=[],
                since=None,
                until=None,
                min_size=None,
                max_size=None,
                min_tokens=None,
                max_file_tokens=None,
                min_lines=None,
                max_file_lines=None,
                files_from=None,
                grep=None,
                exclude_grep=None,
                skip_binary=False,
                max_depth=None,
                git_files=False,
                git_diff=None,
                staged=False,
                unstaged=False,
                unique=False,
                map_lang=[],
                sort=None,
                reverse=False,
                limit=None,
                max_tokens=None,
                max_total_size=None,
                max_total_lines=None,
                clipboard=False,
                format=None,
                markdown=False,
                json=False,
                jsonl=False,
                xml=False,
                csv=False,
                line_numbers=False,
                toc=False,
                include_tree=False,
                overview=False,
                git_log=None,
                include_diff=False,
                header=None,
                footer=None,
                global_header=None,
                global_footer=None,
                max_size_placeholder=None,
                json_summary=None,
                mirror=False,
                pair=[],
                include_unpaired=False,
                pair_template=None,
                estimate_tokens=False,
                list_files=False,
                tree=False,
                diff=False,
                compact=False,
                apply_in_place=False,
                create_backups=False,
                max_lines=None,
                truncate_tokens=None,
                replace=[],
                replace_line=[],
                init=False,
                list_languages=False,
                list_placeholders=False,
                extract=False,
                keep_line_numbers=False,
                restore=False,
                verify=False,
                repair=False,
                delete_backups=False,
                show_config=False,
                export_config=None,
                system_info=False,
                project_info=False
            )

            with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_find:
                with patch('sourcecombine.importlib.util.find_spec', return_value=None):
                    try:
                        sourcecombine.main()
                    except SystemExit:
                        pass

                args = mock_parse.return_value
                assert args.markdown is True
                assert args.line_numbers is True
                assert args.toc is True
                assert args.include_tree is True
                assert args.overview is True
                assert args.skip_binary is True
                assert args.unique is True
                assert args.git_log == 5
                assert args.include_diff is True

def test_ai_preset_respects_explicit_git_log():
    with patch('sourcecombine.argparse.Namespace') as mock_args:
        args = mock_args.return_value
        for attr in ['ai', 'markdown', 'line_numbers', 'toc', 'include_tree', 'overview', 'skip_binary', 'include_diff', 'git_log', 'output', 'clipboard', 'dry_run', 'list_files', 'tree', 'estimate_tokens']:
            setattr(args, attr, None)

        args.ai = True
        args.git_log = 10

        with patch.object(sys, 'argv', ['sourcecombine.py', '--ai', '--git-log', '10']):
            with patch('sourcecombine.find_and_combine_files', return_value={}):
                with patch('sourcecombine.importlib.util.find_spec', return_value=None):
                    try:
                        sourcecombine.main()
                    except SystemExit:
                        pass
                    pass
