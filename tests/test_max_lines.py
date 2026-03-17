import io
import pytest
import copy
from sourcecombine import FileProcessor
import utils

def test_max_lines_truncation(tmp_path):
    """Test that content is truncated to the specified number of lines."""
    file_path = tmp_path / "test.txt"
    content = "line1\nline2\nline3\nline4\nline5\n"
    file_path.write_text(content, encoding='utf-8')

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing']['max_lines'] = 2

    buffer = io.StringIO()
    processor = FileProcessor(config, config['output'])

    # Truncate to 2 lines
    tokens, approx, lines = processor.process_and_write(file_path, tmp_path, buffer)
    assert lines == 2

    # Verify content in buffer (ignoring template)
    # FileProcessor._emit_entry writes to outfile
    # We need to capture what was written
    output = buffer.getvalue()
    assert "line1\nline2\n" in output
    assert "line3" not in output

def test_max_lines_no_truncation(tmp_path):
    """Test that content is NOT truncated if max_lines is 0 or exceeds actual line count."""
    file_path = tmp_path / "test.txt"
    content = "line1\nline2\n"
    file_path.write_text(content, encoding='utf-8')

    # Case 1: max_lines is 0
    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing']['max_lines'] = 0
    buffer = io.StringIO()
    processor = FileProcessor(config, config['output'])
    processor.process_and_write(file_path, tmp_path, buffer)
    assert "line1\nline2\n" in buffer.getvalue()

    # Case 2: max_lines exceeds actual lines
    config['processing']['max_lines'] = 10
    buffer = io.StringIO()
    processor = FileProcessor(config, config['output'])
    processor.process_and_write(file_path, tmp_path, buffer)
    assert "line1\nline2\n" in buffer.getvalue()

def test_max_lines_in_place(tmp_path):
    """Test that in-place updates respect max_lines."""
    file_path = tmp_path / "test.txt"
    content = "1\n2\n3\n4\n"
    file_path.write_text(content, encoding='utf-8')

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing']['max_lines'] = 2
    config['processing']['apply_in_place'] = True
    config['processing']['create_backups'] = False

    buffer = io.StringIO()
    processor = FileProcessor(config, config['output'])
    processor.process_and_write(file_path, tmp_path, buffer)

    # Check the file itself
    updated_content = file_path.read_text(encoding='utf-8')
    assert updated_content == "1\n2\n"

def test_max_lines_validation():
    """Test that max_lines validation works."""
    from utils import validate_config, InvalidConfigError

    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    # Valid
    config['processing']['max_lines'] = 5
    validate_config(config)

    # Invalid: Negative
    config['processing']['max_lines'] = -1
    with pytest.raises(InvalidConfigError, match="'processing.max_lines' must be 0 or more"):
        validate_config(config)

    # Invalid: Not an integer
    config['processing']['max_lines'] = "five"
    with pytest.raises(InvalidConfigError, match="'processing.max_lines' must be 0 or more"):
        validate_config(config)
