import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
from utils import (
    validate_config,
    InvalidConfigError,
    _validate_pairing_section,
    load_yaml_config,
    compact_whitespace,
)
from sourcecombine import (
    _update_file_stats,
    _group_paths_by_stem_suffix,
    find_and_combine_files,
)

def test_validate_config_missing_required_keys():
    """Test utils.validate_config with missing top-level required_keys."""
    config = {"key1": "val1"}
    required_keys = ["key1", "key2"]
    with pytest.raises(InvalidConfigError, match="Config is missing required keys: key2"):
        validate_config(config, required_keys=required_keys)

def test_validate_config_output_not_dict():
    """Test utils.validate_config with an invalid (non-dictionary) output section."""
    config = {"output": "not_a_dict", "search": {"root_folders": ["."]}}
    # This should return early without raising an error, but it hits the 'if not isinstance(output_conf, dict): return' branch
    validate_config(config)

def test_validate_config_search_not_dict():
    """Test utils.validate_config with an invalid (non-dictionary) search section."""
    config = {"pairing": {"enabled": True}, "search": None}
    # This hits 'if not isinstance(search_conf, dict): search_conf = {}' in _validate_filters_section
    validate_config(config)
    assert isinstance(config["search"], dict)

def test_validate_pairing_section_search_not_dict():
    """Test _validate_pairing_section directly with an invalid search section to hit redundant branch."""
    config = {"pairing": {"enabled": True}, "search": None}
    _validate_pairing_section(config)
    assert isinstance(config["search"], dict)

def test_validate_output_table_of_contents_not_bool():
    """Test utils.validate_config with a non-boolean table_of_contents."""
    config = {
        "output": {"table_of_contents": "not_a_bool"},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="'output.table_of_contents' must be a boolean value"):
        validate_config(config)

def test_validate_config_deprecated_in_place_groups():
    """Test utils.validate_config with the deprecated processing.in_place_groups option."""
    config = {
        "processing": {"in_place_groups": ["something"]},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="'processing.in_place_groups' has been deprecated"):
        validate_config(config)

def test_validate_filters_max_total_tokens_invalid():
    """Test filters.max_total_tokens validation."""
    config = {
        "filters": {"max_total_tokens": -1},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="filters.max_total_tokens must be a non-negative integer"):
        validate_config(config)

def test_validate_filters_search_not_dict():
    """Test _validate_filters_section when search is not a dict."""
    config = {
        "filters": {"inclusion_groups": {"test": {"filenames": ["*.py"]}}},
        "search": None
    }
    validate_config(config)
    assert isinstance(config["search"], dict)

def test_load_yaml_config_empty(tmp_path):
    """Test utils.load_yaml_config with an empty file."""
    empty_file = tmp_path / "empty.yml"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(InvalidConfigError, match="Configuration file is empty or invalid"):
        load_yaml_config(empty_file)

def test_compact_whitespace_group_none():
    """Test utils.compact_whitespace when a group value is None."""
    # When value is None, it should return True
    text = "    "
    # spaces_to_tabs is True by default. If we set it to None, it should still be True.
    # We disable trim_trailing_whitespace so we can see the tab.
    result = compact_whitespace(text, groups={"spaces_to_tabs": None, "trim_trailing_whitespace": False})
    assert result == "\t"

def test_validate_pairing_section_conflict():
    """Test utils._validate_pairing_section for the conflict between pairing.enabled and search.allowed_extensions."""
    config = {
        "pairing": {"enabled": True},
        "search": {"root_folders": ["."], "allowed_extensions": [".txt"]}
    }
    with pytest.raises(InvalidConfigError, match="'allowed_extensions' cannot be used when pairing is enabled"):
        validate_config(config)

def test_update_file_stats_oserror():
    """Test sourcecombine._update_file_stats handling of OSError when a file's stats cannot be retrieved."""
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {}
    }
    file_path = MagicMock(spec=Path)
    file_path.stat.side_effect = OSError("Permission denied")
    file_path.suffix = ".txt"

    _update_file_stats(stats, file_path)

    assert stats['total_files'] == 1
    assert stats['total_size_bytes'] == 0
    assert stats['files_by_extension'][".txt"] == 1

def test_group_paths_by_stem_suffix_not_relative():
    """Test sourcecombine._group_paths_by_stem_suffix handling of files that are not relative to the provided root path."""
    root_path = Path("/app/project")
    file_path = Path("/other/outside.txt")

    # This should hit the 'except ValueError' branch in _group_paths_by_stem_suffix
    grouped = _group_paths_by_stem_suffix([file_path], root_path=root_path)

    expected_stem = Path("/other/outside")
    assert expected_stem in grouped
    assert grouped[expected_stem][".txt"] == [file_path]

def test_token_budget_with_global_header(tmp_path, monkeypatch):
    """Verify that the token budget accounts for the global header."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("1234", encoding="utf-8") # 1 token

    # Force fallback mode for deterministic counts
    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    # global header "abcd" = 1 token
    # total budget 1 token. global header takes it all.
    # file1.txt should be excluded or budget exceeded.
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 1},
        "output": {
            "file": str(out_file),
            "global_header_template": "abcd",
            "format": "text"
        }
    }

    stats = find_and_combine_files(
        config,
        output_path=str(out_file)
    )

    # In this case, the first file might still be included because of the 'large first file' logic
    # but the budget should be exceeded.
    assert stats['budget_exceeded'] is True
