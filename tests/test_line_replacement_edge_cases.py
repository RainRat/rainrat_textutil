import sys
import os
import textwrap
from pathlib import Path
import pytest

# Ensure project root is in path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from utils import _replace_line_block, apply_line_regex_replacements, validate_regex_pattern, InvalidConfigError

def test_replace_line_block_removes_block_when_replacement_is_none():
    """Verify that a block of lines is removed when replacement is None."""
    text = textwrap.dedent(
        """
        keep 1
        # remove 1
        # remove 2
        keep 2
        """
    ).strip()
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement=None)
    assert result == "keep 1\nkeep 2"

def test_replace_line_block_removes_block_at_end_of_file():
    """Verify that a block at the very end of the file is correctly removed."""
    text = textwrap.dedent(
        """
        keep
        # remove
        """
    ).strip()
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement=None)
    assert result == "keep"

def test_replace_line_block_preserves_trailing_newline_after_removal():
    """Verify that the trailing newline of the file is preserved even if the last block is removed."""
    text = "keep\n# remove\n"
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement=None)
    assert result == "keep\n"

def test_replace_line_block_preserves_trailing_newline_no_removal():
    """Verify that trailing newline is preserved when no changes are made."""
    text = "keep\n"
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement=None)
    assert result == "keep\n"

def test_replace_line_block_handles_file_starting_with_block():
    """Verify behavior when the file starts with a matching block."""
    text = "# remove\nkeep"
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement=None)
    assert result == "keep"

def test_replace_line_block_replaces_block_at_end_of_file():
    """Verify that replacement is appended correctly when block is at the end."""
    text = "keep\n# match"
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement="<replaced>")
    assert result == "keep\n<replaced>"

def test_replace_line_block_handles_consecutive_blocks_as_one_if_regex_matches():
    """
    Verify that consecutive lines matching the regex are treated as a single block.
    This is inherent to the logic: as long as it matches, it's in the block.
    """
    text = "keep\n# match 1\n# match 2\nkeep"
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement="<replaced>")
    assert result == "keep\n<replaced>\nkeep"

def test_replace_line_block_handles_separated_blocks():
    """Verify that non-contiguous blocks are treated separately."""
    text = "# match 1\nkeep\n# match 2"
    regex = validate_regex_pattern(r"^#")
    result = _replace_line_block(text, regex, replacement="<replaced>")
    assert result == "<replaced>\nkeep\n<replaced>"

def test_apply_line_regex_replacements_skips_invalid_rules():
    """Verify that apply_line_regex_replacements skips rules without patterns."""
    text = "content"
    rules = [
        {"replacement": "foo"}, # Missing pattern
        {"pattern": "content", "replacement": "bar"}
    ]
    # Should skip first rule, apply second
    result = apply_line_regex_replacements(text, rules)
    assert result == "bar"

def test_apply_line_regex_replacements_raises_on_invalid_regex():
    """Verify that invalid regex patterns in rules raise InvalidConfigError."""
    text = "content"
    rules = [{"pattern": "["}] # Invalid regex
    with pytest.raises(InvalidConfigError):
        apply_line_regex_replacements(text, rules)
