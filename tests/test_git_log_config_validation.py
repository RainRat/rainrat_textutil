import pytest
import utils

def test_validate_output_git_log_count_invalid_type():
    """Ensure utils.InvalidConfigError is raised if output.git_log_count is not an integer."""
    config = {
        "search": {"root_folders": ["."]},
        "output": {
            "git_log_count": "5"
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."):
        utils.validate_config(config)

def test_validate_output_git_log_count_negative():
    """Ensure utils.InvalidConfigError is raised if output.git_log_count is negative."""
    config = {
        "search": {"root_folders": ["."]},
        "output": {
            "git_log_count": -1
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."):
        utils.validate_config(config)
