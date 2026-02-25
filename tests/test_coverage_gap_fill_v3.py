import pytest
import sys
import logging
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import utils
from sourcecombine import main, InvalidConfigError

def test_parse_time_value_empty_string():
    assert utils.parse_time_value("") == 0.0

def test_parse_time_value_invalid_date_format():
    with pytest.raises(InvalidConfigError) as exc:
        utils.parse_time_value("2024-13-45")
    assert "Invalid date format" in str(exc.value)

@pytest.mark.parametrize("value,expected_delta", [
    ("10s", 10),
    ("2m", 120),
    ("1w", 7 * 24 * 3600),
])
def test_parse_time_value_units(value, expected_delta):
    val = utils.parse_time_value(value)
    assert time.time() - val == pytest.approx(expected_delta, abs=10)

def test_parse_time_value_unknown_unit_unreachable_branch():
    with patch('re.match') as mock_match:
        mock_m = MagicMock()
        mock_m.group.side_effect = lambda i: "10" if i == 1 else "x"
        mock_match.side_effect = [None, mock_m]
        with pytest.raises(InvalidConfigError) as exc:
            utils.parse_time_value("10x")
        assert "Unknown time unit: 'x'" in str(exc.value)

def test_main_time_filtering_cli_since(tmp_path):
    out_file = tmp_path / "out.txt"
    with patch.object(sys, 'argv', ['sourcecombine.py', '.', '-o', str(out_file), '--since', '2024-01-01']):
        with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
            main()
            config = mock_combine.call_args[0][0]
            assert config['filters']['modified_since'] == utils.parse_time_value('2024-01-01')

def test_main_time_filtering_cli_error_handling(caplog):
    caplog.set_level(logging.ERROR)
    with patch.object(sys, 'argv', ['sourcecombine.py', '--since', 'invalid']):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
        assert "Invalid time value" in caplog.text

def test_main_time_filtering_cli_until(tmp_path):
    out_file = tmp_path / "out.txt"
    with patch.object(sys, 'argv', ['sourcecombine.py', '.', '-o', str(out_file), '--until', '1h']):
        with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
            main()
            config = mock_combine.call_args[0][0]
            assert config['filters']['modified_until'] == pytest.approx(utils.parse_time_value('1h'), abs=1)

def test_main_time_filtering_no_filters_dict(tmp_path):
    out_file = tmp_path / "out.txt"
    with patch.object(sys, 'argv', ['sourcecombine.py', '.', '-o', str(out_file), '--since', '2024-01-01']):
        with patch('sourcecombine.load_and_validate_config', return_value={'search': {'root_folders': ['.']}, 'output': {}}):
            with patch('sourcecombine.find_and_combine_files', return_value={}) as mock_combine:
                main()
                config = mock_combine.call_args[0][0]
                assert 'filters' in config
                assert config['filters']['modified_since'] == utils.parse_time_value('2024-01-01')
