import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils

import pytest


def test_parse_size_value_invalid_numeric():
    # Test that invalid numeric strings that pass the regex raise utils.InvalidConfigError
    # instead of a raw ValueError during float conversion.
    with pytest.raises(utils.InvalidConfigError) as excinfo:
        utils.parse_size_value("10.20.30KB")
    assert "Invalid size value" in str(excinfo.value)
    assert "10.20.30KB" in str(excinfo.value)

def test_parse_size_value_invalid_numeric_no_unit():
    with pytest.raises(utils.InvalidConfigError) as excinfo:
        utils.parse_size_value("10.20.30")
    assert "Invalid size value" in str(excinfo.value)
    assert "10.20.30" in str(excinfo.value)
