import sys
import yaml
import pytest
from unittest.mock import patch
import sourcecombine
from utils import remove_line_numbers, InvalidConfigError

def test_remove_line_numbers_empty_string():
    # Covers utils.py line 835
    assert remove_line_numbers("") == ""

def test_remove_line_numbers_trailing_newline():
    # Covers utils.py line 853
    text = "1: line\n2: second\n"
    expected = "line\nsecond\n"
    assert remove_line_numbers(text) == expected

def test_main_verbose_invalid_config_error(caplog):
    # Covers sourcecombine.py line 2571
    with patch("sourcecombine.load_and_validate_config", return_value={'search': {}}):
        with patch("sourcecombine.validate_config", side_effect=InvalidConfigError("Test Error")):
            with patch("sys.argv", ["sourcecombine.py", "--verbose", "."]):
                with pytest.raises(SystemExit) as excinfo:
                    sourcecombine.main()
                assert excinfo.value.code == 1

    assert "The configuration is not valid: Test Error" in caplog.text

def test_main_malformed_config_injection(capsys):
    # Covers lines 2595, 2600, 2610, 2623, 2649, 2658
    malformed_config = {
        'search': {'root_folders': ['.']},
        'filters': {
            'exclusions': None,
            'inclusion_groups': None
        },
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }

    with patch("sourcecombine.load_and_validate_config", return_value=malformed_config):
        with patch("sys.argv", ["sourcecombine.py", "-x", "file.txt", "-X", "dir", "-i", "inc.txt", "--show-config"]):
            with pytest.raises(SystemExit):
                sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert isinstance(config['filters']['exclusions'], dict)
    assert "file.txt" in config['filters']['exclusions']['filenames']
    assert "dir" in config['filters']['exclusions']['folders']
    assert "_cli_includes" in config['filters']['inclusion_groups']

    no_filters_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }
    with patch("sourcecombine.load_and_validate_config", return_value=no_filters_config):
        with patch("sys.argv", ["sourcecombine.py", "--max-total-size", "1KB", "--max-total-lines", "10", "--show-config"]):
            with pytest.raises(SystemExit):
                sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert isinstance(config['filters'], dict)
    assert config['filters']['max_total_size_bytes'] == 1024
    assert config['filters']['max_total_lines'] == 10

def test_main_empty_root_folders_summary_desc():
    # Covers sourcecombine.py line 2934
    stats = {
        'total_files': 1,
        'files_by_extension': {'.txt': 1},
        'total_size_bytes': 10,
        'tokens_by_extension': {'.txt': 5},
        'size_by_extension': {'.txt': 10},
        'total_tokens': 5,
        'total_lines': 2,
        'top_files': [(5, 10, 'test.txt')],
        'filter_reasons': {}
    }
    config = {
        'search': {'root_folders': []},
        'filters': {},
        'logging': {'level': 'INFO'},
        'pairing': {'enabled': False},
        'output': {'file': 'out.txt'}
    }

    with patch("sourcecombine.load_and_validate_config", return_value=config):
        with patch("sourcecombine.find_and_combine_files", return_value=stats):
            with patch("sys.argv", ["sourcecombine.py", "--exclude-grep", "pattern", "."]):
                sourcecombine.main()
