import pytest
from pathlib import Path
from unittest.mock import MagicMock
import time
from datetime import datetime, timedelta
import utils
import sourcecombine

def test_parse_time_value():
    # Test relative durations
    now = datetime.now().timestamp()

    # 1h should be approx 3600s ago
    val = utils.parse_time_value("1h")
    assert now - val == pytest.approx(3600, abs=10)

    # 1d should be approx 86400s ago
    val = utils.parse_time_value("1d")
    assert now - val == pytest.approx(86400, abs=10)

    # Test absolute date
    val = utils.parse_time_value("2024-01-01")
    expected = datetime(2024, 1, 1).timestamp()
    assert val == expected

    # Test raw seconds
    val = utils.parse_time_value("12345")
    assert val == 12345.0

    # Test invalid format
    with pytest.raises(utils.InvalidConfigError):
        utils.parse_time_value("invalid")

def test_should_include_time_filtering():
    filter_opts = {
        'modified_since': 1000,
        'modified_until': 2000
    }
    search_opts = {}

    # File in range
    mock_path = MagicMock(spec=Path)
    mock_path.is_file.return_value = True
    mock_path.stat.return_value.st_size = 100
    mock_path.stat.return_value.st_mtime = 1500
    mock_path.resolve.return_value = mock_path
    mock_path.name = "test.txt"
    mock_path.suffix = ".txt"
    mock_path.parts = ("test.txt",)
    mock_path.as_posix.return_value = "test.txt"

    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is True

    # Too old
    mock_path.stat.return_value.st_mtime = 500
    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is False
    res, reason = sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'modified_since'

    # Too new
    mock_path.stat.return_value.st_mtime = 2500
    assert sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts) is False
    res, reason = sourcecombine.should_include(mock_path, Path("test.txt"), filter_opts, search_opts, return_reason=True)
    assert res is False
    assert reason == 'modified_until'

def test_config_validation_for_time_filters():
    config = {
        'filters': {
            'modified_since': 123.45,
            'modified_until': 'invalid'
        }
    }
    with pytest.raises(utils.InvalidConfigError) as excinfo:
        utils.validate_config(config)
    assert "filters.modified_until must be a non-negative number" in str(excinfo.value)

    config['filters']['modified_until'] = 200
    utils.validate_config(config) # Should pass now
