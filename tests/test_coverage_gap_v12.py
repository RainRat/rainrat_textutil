import pytest
from unittest.mock import patch, MagicMock
from sourcecombine import main
import utils
from io import StringIO
import sys

def test_main_truncate_tokens_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "test.py").write_text("print('hello')", encoding='utf-8')

    # We use --dry-run to avoid writing output
    with patch('sys.argv', ['sourcecombine.py', '--truncate-tokens', '100', '--dry-run', str(tmp_path)]):
        with patch('sourcecombine.find_and_combine_files') as mock_combine:
            mock_combine.return_value = {'total_included': 1, 'files_by_extension': {'.py': 1}}
            try:
                main()
            except SystemExit:
                pass

            # Verify the config passed to find_and_combine_files
            args, _ = mock_combine.call_args
            config = args[0]
            assert config['processing']['max_tokens'] == 100

def test_validate_search_custom_languages_success():
    config = {
        'search': {
            'custom_languages': {
                '.MYEXT': 'python',
                'HeaderFile.H': 'cpp'
            }
        }
    }
    utils.validate_config(config)
    # Check normalization to lowercase
    assert config['search']['custom_languages']['.myext'] == 'python'
    assert config['search']['custom_languages']['headerfile.h'] == 'cpp'

def test_validate_processing_max_tokens_invalid():
    config = {
        'processing': {
            'max_tokens': -1
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="'processing.max_tokens' must be 0 or more"):
        utils.validate_config(config)

    config['processing']['max_tokens'] = "not an int"
    with pytest.raises(utils.InvalidConfigError, match="'processing.max_tokens' must be 0 or more"):
        utils.validate_config(config)

def test_truncate_tokens_shorter_than_limit_with_tiktoken():
    mock_tiktoken = MagicMock()
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3] # 3 tokens
    mock_tiktoken.get_encoding.return_value = mock_encoding

    with patch('utils.tiktoken', mock_tiktoken):
        text = "some text"
        result = utils.truncate_tokens(text, 5) # limit 5 > 3
        assert result == text
        mock_encoding.encode.assert_called_once()

def test_truncate_tokens_tiktoken_exception():
    mock_tiktoken = MagicMock()
    mock_tiktoken.get_encoding.side_effect = Exception("Tiktoken failure")

    with patch('utils.tiktoken', mock_tiktoken):
        text = "word " * 10 # 50 chars
        # 10 tokens limit -> 40 chars limit in fallback
        result = utils.truncate_tokens(text, 10)
        assert result == text[:40]
        assert len(result) == 40

def test_truncate_tokens_shorter_than_limit_fallback():
    with patch('utils.tiktoken', None):
        text = "short"
        # limit 10 tokens -> 40 chars limit
        result = utils.truncate_tokens(text, 10)
        assert result == text
