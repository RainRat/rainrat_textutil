from sourcecombine import _generate_project_overview, main, find_and_combine_files
import pytest
import sys
import logging
import os
from io import StringIO
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_generate_project_overview_empty_stats():
    assert _generate_project_overview(None) == ""
    assert _generate_project_overview({}) == ""

def test_generate_project_overview_all_truncations_text():
    stats = {
        'total_files': 10,
        'total_size_bytes': 1024,
        'total_tokens': 100,
        'total_lines': 50,
        'token_limit_reached': True,
        'size_limit_reached': True,
        'line_limit_reached': True,
        'limit_reached': True
    }
    overview = _generate_project_overview(stats, output_format='text')
    assert "WARNING: Output shortened due to: token limit, total size limit, total line limit, file limit" in overview

def test_generate_project_overview_all_truncations_markdown():
    stats = {
        'total_files': 10,
        'total_size_bytes': 1024,
        'total_tokens': 100,
        'total_lines': 50,
        'token_limit_reached': True,
        'size_limit_reached': True,
        'line_limit_reached': True,
        'limit_reached': True
    }
    overview = _generate_project_overview(stats, output_format='markdown')
    assert "> [!CAUTION]" in overview
    assert "**WARNING: Output shortened due to: token limit, total size limit, total line limit, file limit**" in overview

def test_generate_project_overview_applied_processing_markdown():
    stats = {'total_files': 1}
    processing_opts = {
        'compact_whitespace': True,
        'remove_all_c_style_comments': True,
        'max_lines': 100
    }
    overview = _generate_project_overview(stats, output_format='markdown', processing_opts=processing_opts)
    assert "## Applied Processing" in overview
    assert "- Whitespace compaction" in overview
    assert "- C-style comment removal" in overview
    assert "- Shortened to 100 lines per file" in overview

def test_generate_project_overview_c_style_comment_removal_text():
    stats = {'total_files': 1}
    processing_opts = {'remove_all_c_style_comments': True}
    overview = _generate_project_overview(stats, output_format='text', processing_opts=processing_opts)
    assert "C-style comment removal" in overview

def test_validate_config_project_overview_non_bool():
    import utils
    config = {
        'search': {'root_folders': ['.']},
        'output': {'project_overview': 'not-a-bool'}
    }
    with pytest.raises(utils.InvalidConfigError, match="'output.project_overview' must be true or false"):
        utils.validate_config(config)

def test_get_tqdm_import_error():
    import sourcecombine
    with patch.dict(sys.modules, {'tqdm': None}):
        assert sourcecombine._get_tqdm() is None


def test_get_pyperclip_import_error():
    import sourcecombine
    with patch.dict(sys.modules, {'pyperclip': None}):
        assert sourcecombine._get_pyperclip() is None

def test_clipboard_missing_pyperclip_error(caplog):
    import sourcecombine
    caplog.set_level(logging.ERROR)
    with patch('sourcecombine._get_pyperclip', return_value=None):
        sourcecombine.find_and_combine_files(
            {'search': {'root_folders': []}, 'output': {}},
            None,
            clipboard=True
        )
    assert "The 'pyperclip' tool is required for clipboard support" in caplog.text

def test_main_init_missing_yaml(tmp_path, caplog, monkeypatch):
    import sourcecombine
    import utils
    caplog.set_level(logging.WARNING)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sourcecombine, "__file__", str(tmp_path / "fake_script.py"))

    with patch('utils.yaml', None):
        with patch('sys.argv', ['sourcecombine.py', '--init']):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0

    assert "PyYAML not found; creating an empty configuration" in caplog.text

def test_main_show_config_missing_yaml(caplog):
    import sourcecombine
    import utils
    caplog.set_level(logging.INFO)

    config = {'search': {'root_folders': ['.']}, 'output': {}}
    with patch('sourcecombine.load_and_validate_config', return_value=config):
        with patch('utils.yaml', None):
            with patch('sys.argv', ['sourcecombine.py', '--show-config']):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    with pytest.raises(SystemExit):
                        main()
                    output = mock_stdout.getvalue()
                    assert '"search":' in output

def test_main_extract_clipboard_paste_missing_pyperclip(caplog, tmp_path, monkeypatch):
    import sourcecombine
    caplog.set_level(logging.ERROR)
    monkeypatch.chdir(tmp_path)

    with patch('sourcecombine._get_pyperclip', return_value=None):
        with patch('sys.argv', ['sourcecombine.py', '--extract', '--clipboard']):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
    assert "The 'pyperclip' tool is required for clipboard support" in caplog.text

def test_main_extract_clipboard_paste_error(caplog, tmp_path, monkeypatch):
    import sourcecombine
    caplog.set_level(logging.ERROR)
    monkeypatch.chdir(tmp_path)

    mock_pyperclip = MagicMock()
    mock_pyperclip.paste.side_effect = Exception("Paste failed")
    with patch('sourcecombine._get_pyperclip', return_value=mock_pyperclip):
        with patch('sys.argv', ['sourcecombine.py', '--extract', '--clipboard']):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 1
    assert "Failed to paste from clipboard: Paste failed" in caplog.text

def test_terminal_summary_approx_tokens(capsys):
    import sourcecombine
    from argparse import Namespace

    stats = {
        'total_included': 1,
        'total_size_bytes': 100,
        'total_tokens': 1000,
        'token_count_is_approx': True,
        'files_by_extension': {'.py': 1},
    }
    args = Namespace(
        dry_run=False,
        estimate_tokens=False,
        list_files=False,
        tree=False,
        clipboard=False,
        git_log=None,
    )

    sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    assert "~1,000 tokens" in captured.err

def test_find_and_combine_with_overview_approx_tokens_v3(tmp_path):
    # Create a dummy file
    (tmp_path / "file1.py").write_text("print('hello')", encoding='utf-8')
    output_file = tmp_path / "combined.txt"

    config = {
        'search': {'root_folders': [str(tmp_path)]},
        'output': {
            'project_overview': True,
            'format': 'text',
            'file': str(output_file)
        }
    }

    # Mock estimate_tokens to always return is_approx=True
    with patch('sourcecombine.utils.estimate_tokens', return_value=(100, True)):
        stats = find_and_combine_files(config, str(output_file), estimate_tokens=True)
        assert stats.get('token_count_is_approx') is True
