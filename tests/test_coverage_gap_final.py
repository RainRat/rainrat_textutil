import sys
import yaml
import pytest
from unittest.mock import patch, MagicMock
import sourcecombine
from utils import remove_line_numbers, InvalidConfigError, process_content, validate_config

def test_remove_line_numbers_empty_string():
    # Covers utils.py line 835
    assert remove_line_numbers("") == ""

def test_remove_line_numbers_trailing_newline():
    # Covers utils.py line 853
    text = "1: line\n2: second\n"
    expected = "line\nsecond\n"
    assert remove_line_numbers(text) == expected

def test_main_verbose_invalid_config_error(caplog):
    # Covers sourcecombine.py line 2571 (approx)
    with patch("sourcecombine.load_and_validate_config", return_value={'search': {}}):
        with patch("sourcecombine.validate_config", side_effect=InvalidConfigError("Test Error")):
            with patch("sys.argv", ["sourcecombine.py", "--verbose", "."]):
                with pytest.raises(SystemExit) as excinfo:
                    sourcecombine.main()
                assert excinfo.value.code == 1

    assert "The configuration is not valid: Test Error" in caplog.text

def test_main_malformed_config_injection(capsys):
    # Covers sourcecombine.py lines 2595, 2600, 2610, 2623
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
        with patch("sourcecombine.validate_config"):
            with patch("sys.argv", ["sourcecombine.py", "--config", "dummy.yml", "-x", "file.txt", "-X", "dir", "-i", "inc.txt", "--show-config"]):
                with pytest.raises(SystemExit):
                    sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert isinstance(config['filters']['exclusions'], dict)
    assert "file.txt" in config['filters']['exclusions']['filenames']
    assert "dir" in config['filters']['exclusions']['folders']
    assert "_cli_includes" in config['filters']['inclusion_groups']

def test_main_injection_max_total_size(capsys):
    # Covers sourcecombine.py line 2653
    no_filters_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }
    with patch("sourcecombine.load_and_validate_config", return_value=no_filters_config):
        with patch("sourcecombine.validate_config"):
            with patch("sys.argv", ["sourcecombine.py", "--config", "dummy.yml", "--max-total-size", "1KB", "--show-config"]):
                with pytest.raises(SystemExit):
                    sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config['filters']['max_total_size_bytes'] == 1024

def test_main_injection_max_total_lines(capsys):
    # Covers sourcecombine.py line 2662
    no_filters_config = {
        'search': {'root_folders': ['.']},
        'logging': {'level': 'INFO'},
        'pairing': {},
        'output': {}
    }
    with patch("sourcecombine.load_and_validate_config", return_value=no_filters_config):
        with patch("sourcecombine.validate_config"):
            with patch("sys.argv", ["sourcecombine.py", "--config", "dummy.yml", "--max-total-lines", "10", "--show-config"]):
                with pytest.raises(SystemExit):
                    sourcecombine.main()

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config['filters']['max_total_lines'] == 10

def test_main_source_desc_empty():
    # Covers sourcecombine.py line 2940
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
        'search': {'root_folders': ['.']},
        'filters': {},
        'logging': {'level': 'INFO'},
        'pairing': {'enabled': False},
        'output': {'file': 'out.txt'}
    }

    def mock_find(cfg, *args, **kwargs):
        # Clear root_folders to trigger the empty source_desc branch
        cfg['search']['root_folders'] = []
        return stats

    with patch("sourcecombine.load_and_validate_config", return_value=config):
        with patch("sourcecombine.find_and_combine_files", side_effect=mock_find):
            with patch("sys.argv", ["sourcecombine.py", "."]):
                with patch("sourcecombine.time.perf_counter", return_value=0):
                    sourcecombine.main()

def test_progress_bar_hits_tqdm():
    # Covers sourcecombine.py line 175
    with patch("sourcecombine._tqdm") as mock_tqdm:
        with patch("sourcecombine._progress_enabled", return_value=True):
            sourcecombine._progress_bar(range(10), enabled=True)
            mock_tqdm.assert_called_once()

def test_utils_process_content_no_options():
    # Covers utils.py line 755
    assert process_content("hello", None) == "hello"
    assert process_content("hello", {}) == "hello"

def test_utils_invalid_use_git():
    # Covers utils.py line 370
    with pytest.raises(InvalidConfigError, match="search.use_git must be true or false"):
        validate_config({'search': {'use_git': 'not a bool'}}, defaults=None)
