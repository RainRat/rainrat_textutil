import utils
import sourcecombine
import pytest

def test_print_diff_identical_content(capsys):
    sourcecombine._print_diff("same content", "same content", "test.txt")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

def test_apply_line_regex_replacements_missing_pattern():
    text = "line1\nline2"
    rules = [{'no_pattern': 'value'}]
    result = utils.apply_line_regex_replacements(text, rules)
    assert result == text

def test_validate_output_show_diff_invalid():
    config = {'output': {'show_diff': 'not-a-bool'}}
    with pytest.raises(utils.InvalidConfigError, match="'output.show_diff' must be true or false."):
        utils._validate_output_section(config)
