import logging
import os
import sys
from pathlib import Path

import pytest
import yaml

# Add the project root to sys.path so we can import utils
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from utils import (
    load_and_validate_config,
    InvalidConfigError,
    apply_line_regex_replacements,
)

def _write_config(tmp_path: Path, data: dict) -> Path:
    """Helper to write a YAML config file."""
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path

def test_validate_compact_whitespace_groups_not_dict(tmp_path):
    """Ensure InvalidConfigError is raised if compact_whitespace_groups is not a dictionary."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace_groups": "not_a_dict"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'processing.compact_whitespace_groups' must be a dictionary"):
        load_and_validate_config(config_path)

def test_validate_compact_whitespace_groups_unknown_key(tmp_path, caplog):
    """Ensure a warning is logged for unknown keys in compact_whitespace_groups."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace_groups": {
                    "unknown_group": True
                }
            }
        }
    )
    with caplog.at_level(logging.WARNING):
        load_and_validate_config(config_path)

    assert "Unknown compact_whitespace_groups entry 'unknown_group'" in caplog.text

def test_validate_compact_whitespace_groups_invalid_value(tmp_path):
    """Ensure InvalidConfigError is raised for non-boolean/non-null values in compact_whitespace_groups."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace_groups": {
                    "spaces_to_tabs": "invalid_value"
                }
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="Values in 'processing.compact_whitespace_groups' must be true, false, or null"):
        load_and_validate_config(config_path)

def test_apply_line_regex_replacements_block_at_eof():
    """Ensure that a matching block at the very end of the string is correctly replaced."""
    text = "line1\nmatch\nmatch"
    rules = [{"pattern": "^match$", "replacement": "replaced"}]

    # The block "match\nmatch" is at the end of the input.
    # The function should detect the end of the block at EOF and append the replacement.
    result = apply_line_regex_replacements(text, rules)
    assert result == "line1\nreplaced"

def test_validate_regex_replacements_invalid_regex(tmp_path):
    """Ensure InvalidConfigError is raised for invalid regex in regex_replacements."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "regex_replacements": [
                    {"pattern": "[invalid_regex", "replacement": "test"}
                ]
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="Invalid regex pattern in processing.regex_replacements\\[0\\]"):
        load_and_validate_config(config_path)

def test_validate_line_regex_replacements_invalid_regex(tmp_path):
    """Ensure InvalidConfigError is raised for invalid regex in line_regex_replacements."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "line_regex_replacements": [
                    {"pattern": "(unclosed group", "replacement": "test"}
                ]
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="Invalid regex pattern in processing.line_regex_replacements\\[0\\]"):
        load_and_validate_config(config_path)

def test_validate_output_format_invalid(tmp_path):
    """Ensure InvalidConfigError is raised for an unsupported output format."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {
                "format": "invalid_format"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'output.format' must be one of: text, json, markdown, xml"):
        load_and_validate_config(config_path)

def test_validate_processing_compact_whitespace_non_bool(tmp_path):
    """Ensure InvalidConfigError is raised if processing.compact_whitespace is not a boolean."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace": "not_a_bool"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'processing.compact_whitespace' must be a boolean value"):
        load_and_validate_config(config_path)

def test_validate_processing_apply_in_place_non_bool(tmp_path):
    """Ensure InvalidConfigError is raised if processing.apply_in_place is not a boolean."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "apply_in_place": "not_a_bool"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'processing.apply_in_place' must be a boolean value"):
        load_and_validate_config(config_path)

def test_validate_output_sort_by_invalid(tmp_path):
    """Ensure InvalidConfigError is raised for an unsupported sort_by value."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {
                "sort_by": "invalid_sort"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'output.sort_by' must be one of: name, size, modified, tokens, depth"):
        load_and_validate_config(config_path)

def test_validate_output_sort_reverse_non_bool(tmp_path):
    """Ensure InvalidConfigError is raised if output.sort_reverse is not a boolean."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {
                "sort_reverse": "not_a_bool"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'output.sort_reverse' must be a boolean value"):
        load_and_validate_config(config_path)

def test_validate_filters_max_files_invalid(tmp_path):
    """Ensure InvalidConfigError is raised if filters.max_files is invalid."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {
                "max_files": -1
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="filters.max_files must be a non-negative integer"):
        load_and_validate_config(config_path)

    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {
                "max_files": "not_an_int"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="filters.max_files must be a non-negative integer"):
        load_and_validate_config(config_path)

def test_validate_config_nested_not_dict(tmp_path):
    """Ensure InvalidConfigError is raised if a required nested section is not a dictionary."""
    from utils import validate_config
    config = {"search": "not_a_dict"}
    with pytest.raises(InvalidConfigError, match="'search' section must be a dictionary with keys: root_folders"):
        validate_config(config, nested_required={"search": ["root_folders"]})
