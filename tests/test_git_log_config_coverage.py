import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils

import pytest
from utils import InvalidConfigError, validate_config


def test_git_log_count_invalid_negative():
    config = {
        "search": {"root_folders": ["."]},
        "output": {"git_log_count": -1},
    }
    with pytest.raises(
        utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."
    ):
        validate_config(config)


def test_git_log_count_invalid_type_string():
    config = {
        "search": {"root_folders": ["."]},
        "output": {"git_log_count": "5"},
    }
    with pytest.raises(
        utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."
    ):
        validate_config(config)


def test_git_log_count_invalid_type_float():
    config = {
        "search": {"root_folders": ["."]},
        "output": {"git_log_count": 5.5},
    }
    with pytest.raises(
        utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."
    ):
        validate_config(config)


def test_git_log_count_boundary_zero():
    config = {
        "search": {"root_folders": ["."]},
        "output": {"git_log_count": 0},
    }
    # Should not raise
    validate_config(config)


def test_git_log_count_valid_positive():
    config = {
        "search": {"root_folders": ["."]},
        "output": {"git_log_count": 5},
    }
    # Should not raise
    validate_config(config)


def test_git_log_count_none():
    config = {
        "search": {"root_folders": ["."]},
        "output": {"git_log_count": None},
    }
    # Should not raise
    validate_config(config)
