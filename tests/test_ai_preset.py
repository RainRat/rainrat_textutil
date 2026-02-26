import pytest
from sourcecombine import main
import sys
from unittest.mock import patch

def get_mock_stats():
    return {
        'total_files': 0,
        'total_discovered': 0,
        'total_size_bytes': 0,
        'files_by_extension': {},
        'total_tokens': 0,
        'total_lines': 0,
        'filter_reasons': {},
        'top_files': []
    }

def test_ai_preset_flag_logic(capsys):
    """Test that the --ai flag correctly enables all specified flags."""
    test_args = ["sourcecombine.py", "--ai", "--dry-run", "test_ai"]

    with patch.object(sys, 'argv', test_args):
        with patch('sys.exit') as mock_exit:
            with patch('sourcecombine.find_and_combine_files') as mock_find:
                mock_find.return_value = get_mock_stats()
                main()

                assert mock_find.called
                _, kwargs = mock_find.call_args

                assert kwargs['output_format'] == 'markdown'
                # Check other flags in config
                config = mock_find.call_args[0][0]
                assert config['output']['add_line_numbers'] is True
                assert config['output']['table_of_contents'] is True
                assert config['output']['include_tree'] is True

def test_ai_preset_shortcut(capsys):
    """Test that the -a shortcut also works."""
    test_args = ["sourcecombine.py", "-a", "--dry-run", "test_ai"]

    with patch.object(sys, 'argv', test_args):
        with patch('sys.exit'):
            with patch('sourcecombine.find_and_combine_files') as mock_find:
                mock_find.return_value = get_mock_stats()
                main()

                assert mock_find.called
                _, kwargs = mock_find.call_args
                assert kwargs['output_format'] == 'markdown'

def test_ai_preset_clipboard_fallback(capsys):
    """Test that --ai enables clipboard if no output is specified."""
    test_args = ["sourcecombine.py", "-a", "--dry-run", "test_ai"]

    with patch.object(sys, 'argv', test_args):
        with patch('sys.exit'):
            with patch('pyperclip.copy'):
                with patch('sourcecombine.find_and_combine_files') as mock_find:
                    mock_find.return_value = get_mock_stats()
                    main()

                    _, kwargs = mock_find.call_args
                    assert kwargs['clipboard'] is True
