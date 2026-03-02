import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import utils
import sourcecombine
import sys

def test_parse_size_value():
    # Basic bytes
    assert utils.parse_size_value("100") == 100
    assert utils.parse_size_value("100B") == 100
    assert utils.parse_size_value("100 b") == 100

    # KB
    assert utils.parse_size_value("1k") == 1024
    assert utils.parse_size_value("1kb") == 1024
    assert utils.parse_size_value("1.5KB") == 1536

    # MB
    assert utils.parse_size_value("1m") == 1024**2
    assert utils.parse_size_value("1mb") == 1024**2
    assert utils.parse_size_value("2.5MB") == int(2.5 * 1024**2)

    # GB
    assert utils.parse_size_value("1g") == 1024**3
    assert utils.parse_size_value("1gb") == 1024**3

    # TB
    assert utils.parse_size_value("1t") == 1024**4
    assert utils.parse_size_value("1tb") == 1024**4

    # Empty
    assert utils.parse_size_value("") == 0
    assert utils.parse_size_value(None) == 0

    # Invalid
    with pytest.raises(utils.InvalidConfigError):
        utils.parse_size_value("invalid")
    with pytest.raises(utils.InvalidConfigError):
        utils.parse_size_value("100XB")

def test_cli_size_config_injection():
    # Test --min-size
    test_args = ["sourcecombine.py", ".", "--min-size", "10KB"]
    with patch.object(sys, 'argv', test_args):
        with patch('sourcecombine.find_and_combine_files') as mock_find:
            mock_find.return_value = {}
            # We need to mock sys.exit because main calls it on success in some paths,
            # but actually main() usually just returns unless there is an error or it's a utility command.
            sourcecombine.main()

            # Check if config was injected correctly
            config = mock_find.call_args[0][0]
            assert config['filters']['min_size_bytes'] == 10240

    # Test --max-size
    test_args = ["sourcecombine.py", ".", "--max-size", "1MB"]
    with patch.object(sys, 'argv', test_args):
        with patch('sourcecombine.find_and_combine_files') as mock_find:
            mock_find.return_value = {}
            sourcecombine.main()

            config = mock_find.call_args[0][0]
            assert config['filters']['max_size_bytes'] == 1024**2

def test_should_include_size_filtering():
    search_opts = {}

    # File exactly at min size
    filter_opts = {'min_size_bytes': 100}
    mock_path = MagicMock(spec=Path)
    mock_path.is_file.return_value = True
    mock_path.stat.return_value.st_size = 100
    mock_path.suffix = ".txt"
    mock_path.name = "test.txt"
    mock_path.parts = ("test.txt",)
    mock_path.as_posix.return_value = "test.txt"
    mock_path.resolve.return_value = mock_path

    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is True

    # File below min size
    mock_path.stat.return_value.st_size = 99
    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is False
    res, reason = sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'too_small'

    # File exactly at max size
    filter_opts = {'max_size_bytes': 100}
    mock_path.stat.return_value.st_size = 100
    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is True

    # File above max size
    mock_path.stat.return_value.st_size = 101
    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is False
    res, reason = sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'too_large'
