import pytest
import utils
import logging
import yaml
from pathlib import Path

def test_validate_output_git_log_count_invalid():
    """Cover utils.py line 758: raise InvalidConfigError for invalid git_log_count."""
    config = {
        'search': {'root_folders': ['.']},
        'output': {'git_log_count': -1}
    }
    with pytest.raises(utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."):
        utils.validate_config(config)

    config['output']['git_log_count'] = "not an int"
    with pytest.raises(utils.InvalidConfigError, match="'output.git_log_count' must be 0 or more."):
        utils.validate_config(config)

def test_process_content_c_style_comment_edge_cases():
    """Cover utils.py lines 914->919 and 916->919."""
    options = {'remove_initial_c_style_comment': True}

    # 914->919: startswith('/*') is False
    text = "int main() {}"
    assert utils.process_content(text, options) == text

    # 916->919: end_index == -1 (unterminated)
    text = "/* unterminated comment\nint x = 1;"
    assert utils.process_content(text, options) == text

def test_looks_binary_edge_cases(tmp_path):
    """Cover utils.py _looks_binary branches."""
    from utils import _looks_binary

    # path is None, sample is None
    assert _looks_binary() is False

    # path exists but cannot be read (mocked or edge case)
    # empty file
    p = tmp_path / "empty"
    p.write_bytes(b"")
    assert _looks_binary(p) is False

    # high non-text ratio
    assert _looks_binary(sample=b"\x01\x02\x03\x04\x05") is True

def test_validate_config_required_keys_satisfied():
    """Cover utils.py line 825->830: missing_keys is empty."""
    config = {'key1': 'val1'}
    utils.validate_config(config, required_keys=['key1'])
    # Should not raise any error

def test_validate_search_section_custom_languages_none():
    """Cover utils.py line 517->exit: custom_languages is None."""
    # We need to bypass the default merging to actually test this branch
    config = {'search': {'root_folders': ['.'], 'custom_languages': None}}
    utils._validate_search_section(config)
    assert config['search']['custom_languages'] is None

def test_validate_processing_section_no_limits():
    """Cover utils.py lines 663->669 and 670->676: max_lines/max_tokens are None."""
    config = {
        'processing': {
            'max_lines': None,
            'max_tokens': None
        }
    }
    utils._validate_processing_section(config)
    assert config['processing'].get('max_lines') is None
    assert config['processing'].get('max_tokens') is None

def test_apply_line_regex_replacements_no_pattern():
    """Cover utils.py line 797-798: if not pattern: continue."""
    rules = [{'replacement': 'something'}]
    assert utils.apply_line_regex_replacements("text", rules) == "text"

def test_load_yaml_config_not_found(tmp_path):
    """Cover utils.py line 206: ConfigNotFoundError."""
    with pytest.raises(utils.ConfigNotFoundError):
        utils.load_yaml_config(tmp_path / "nonexistent.yml")

def test_load_yaml_config_scanner_error_with_hint(tmp_path):
    """Cover utils.py lines 212, 221-222: YAML ScannerError with hint."""
    invalid_yaml = 'search:\n  root_folders: ["./src]' # missing closing quote
    p = tmp_path / "invalid.yml"
    p.write_text(invalid_yaml)
    with pytest.raises(utils.InvalidConfigError, match="Check for missing closing quotes"):
        utils.load_yaml_config(p)

def test_load_yaml_config_yaml_error_no_mark(tmp_path):
    """Cover utils.py line 212->215: YAMLError without mark."""
    from unittest.mock import patch, mock_open
    with patch("builtins.open", mock_open(read_data="foo: bar")):
        with patch("yaml.safe_load", side_effect=yaml.YAMLError("some error")):
            with pytest.raises(utils.InvalidConfigError, match="Error parsing YAML file: some error"):
                utils.load_yaml_config(tmp_path / "fake.yml")

def test_load_yaml_config_scanner_error_no_hint(tmp_path):
    """Cover utils.py line 221->224: ScannerError without 'quoted scalar'."""
    # YAML ScannerError normally has context.
    # We'll mock one.
    from unittest.mock import patch, mock_open
    err = yaml.scanner.ScannerError(context="some context", problem="some problem")
    with patch("builtins.open", mock_open(read_data="foo: bar")):
        with patch("yaml.safe_load", side_effect=err):
            with pytest.raises(utils.InvalidConfigError) as exc:
                utils.load_yaml_config(tmp_path / "fake.yml")
            assert "Check for missing closing quotes" not in str(exc.value)

def test_parse_time_value_raw_number():
    """Cover utils.py line 1259-1260."""
    assert utils.parse_time_value("12345") == 12345.0

def test_parse_size_value_units():
    """Cover utils.py size parsing units G, T."""
    assert utils.parse_size_value("1G") == 1024**3
    assert utils.parse_size_value("1T") == 1024**4

def test_parse_size_value_invalid():
    """Cover utils.py line 1303: Unknown size unit."""
    with pytest.raises(utils.InvalidConfigError, match="Unknown size unit"):
        utils.parse_size_value("1XYZ")

def test_validate_search_section_git_options():
    """Cover utils.py lines 461, 479, 485."""
    config = {'search': {'use_git': True, 'git_staged': True, 'git_unstaged': True}}
    utils._validate_search_section(config)
    # No error

def test_validate_output_show_diff():
    """Cover utils.py line 783."""
    config = {'output': {'show_diff': True}}
    utils._validate_output_section(config)
    # No error

def test_process_content_max_lines_max_tokens():
    """Cover utils.py lines 967, 972."""
    text = "line1\nline2\nline3"
    options = {'max_lines': 2}
    assert utils.process_content(text, options) == "line1\nline2\n"

    options = {'max_tokens': 1}
    # truncate_tokens(text, 1) will give something very short
    result = utils.process_content(text, options)
    assert len(result) < len(text)

def test_validate_compact_whitespace_groups_branches():
    """Cover utils.py line 376->368."""
    groups = {'spaces_to_tabs': True, 'compact_space_runs': None}
    utils._validate_compact_whitespace_groups(groups, context="test")
    # Should pass

def test_validate_regex_list_no_pattern_branch():
    """Cover utils.py line 394->389."""
    rules = [{'replacement': 'something'}]
    utils._validate_regex_list(rules, "test", None)
    # Should pass
