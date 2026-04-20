import pytest
import logging
import yaml
from pathlib import Path
import utils

def test_validate_output_git_log_count_negative():
    config = {
        'output': {'git_log_count': -1},
        'search': {'root_folders': ['.']}
    }
    with pytest.raises(utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."):
        utils.validate_config(config)

def test_validate_search_custom_languages_non_string():
    config = {
        'search': {
            'custom_languages': {123: 'python'}
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="Both keys and values in 'search.custom_languages' must be text."):
        utils.validate_config(config)

    config = {
        'search': {
            'custom_languages': {'.py': 123}
        }
    }
    with pytest.raises(utils.InvalidConfigError, match="Both keys and values in 'search.custom_languages' must be text."):
        utils.validate_config(config)

def test_validate_processing_max_lines_negative():
    config = {
        'processing': {'max_lines': -1},
        'search': {'root_folders': ['.']}
    }
    with pytest.raises(utils.InvalidConfigError, match="'processing.max_lines' must be 0 or more"):
        utils.validate_config(config)

def test_validate_processing_max_tokens_negative():
    config = {
        'processing': {'max_tokens': -1},
        'search': {'root_folders': ['.']}
    }
    with pytest.raises(utils.InvalidConfigError, match="'processing.max_tokens' must be 0 or more"):
        utils.validate_config(config)

def test_load_yaml_config_parser_error(tmp_path):
    # This should trigger a yaml.parser.ParserError, which is not a ScannerError
    # but still has a problem_mark.
    invalid_yaml = tmp_path / "invalid.yml"
    invalid_yaml.write_text("key: val\n  key2: val2", encoding="utf-8") # Indentation error
    with pytest.raises(utils.InvalidConfigError) as exc:
        utils.load_yaml_config(invalid_yaml)
    assert "at line 2, column 7" in str(exc.value)

def test_validate_compact_whitespace_groups_warning(caplog):
    groups = {"unknown_key": True}
    with caplog.at_level(logging.WARNING):
        utils._validate_compact_whitespace_groups(groups, context="test_context")
    assert "Unknown compact_whitespace_groups entry 'unknown_key' in test_context" in caplog.text

def test_validate_search_section_not_dict():
    config = {'search': 'not-a-dict'}
    with pytest.raises(utils.InvalidConfigError, match="'search' section must be a dictionary."):
        utils.validate_config(config)

def test_validate_filters_section_not_dict():
    config = {'filters': 'not-a-dict'}
    with pytest.raises(utils.InvalidConfigError, match="'filters' section must be a dictionary."):
        utils.validate_config(config)

def test_validate_processing_section_not_dict():
    config = {'processing': 'not-a-dict'}
    with pytest.raises(utils.InvalidConfigError, match="'processing' section must be a dictionary."):
        utils.validate_config(config)

def test_process_content_initial_c_comment_no_match():
    # Covers 914->919 branch (doesn't start with /*)
    text = "int main() {}"
    options = {'remove_initial_c_style_comment': True}
    assert utils.process_content(text, options) == text

def test_process_content_initial_c_comment_unterminated():
    # Covers 916->919 branch (starts with /* but no */)
    text = "/* unterminated"
    options = {'remove_initial_c_style_comment': True}
    assert utils.process_content(text, options) == text

def test_validate_regex_list_missing_pattern():
    # Covers 394->389 branch
    rules = [{'replacement': 'something'}]
    utils._validate_regex_list(rules, "test", None)

def test_validate_search_section_no_custom_langs():
    # Covers 517->exit branch
    config = {'search': {}}
    utils._validate_search_section(config)

def test_validate_config_no_missing_keys():
    # Covers 825->830 branch
    config = {'key': 'val'}
    utils.validate_config(config, required_keys=['key'])

def test_validate_compact_whitespace_groups_valid():
    # Covers 376->368 branch (valid boolean value)
    groups = {"compact_space_runs": True}
    utils._validate_compact_whitespace_groups(groups, context="test")

def test_validate_compact_whitespace_groups_none():
    # Covers 376->368 branch (None value)
    groups = {"compact_space_runs": None}
    utils._validate_compact_whitespace_groups(groups, context="test")

def test_load_yaml_config_no_mark():
    # Covers 212->215 branch (YAMLError without mark)
    from unittest.mock import patch, mock_open
    with patch("builtins.open", mock_open(read_data="key: value")):
        with patch("yaml.safe_load", side_effect=yaml.YAMLError("General error")):
            with pytest.raises(utils.InvalidConfigError):
                utils.load_yaml_config("dummy.yml")

def test_load_yaml_config_scanner_error_no_quoted_scalar():
    # Covers 221->224 branch (ScannerError with context but no 'quoted scalar')
    from yaml.scanner import ScannerError
    err = ScannerError(context="some context", problem="some problem")
    from unittest.mock import patch, mock_open
    with patch("builtins.open", mock_open(read_data="key: value")):
        with patch("yaml.safe_load", side_effect=err):
            with pytest.raises(utils.InvalidConfigError):
                utils.load_yaml_config("dummy.yml")

def test_validate_processing_section_max_lines_none():
    # Covers 663->669 branch
    config = {'processing': {'max_lines': None}}
    utils._validate_processing_section(config)

def test_validate_processing_section_max_tokens_none():
    # Covers 670->676 branch
    config = {'processing': {'max_tokens': None}}
    utils._validate_processing_section(config)
