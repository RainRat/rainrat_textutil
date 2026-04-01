import sys
import os
from pathlib import Path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import pytest
import utils
from sourcecombine import should_include

def test_min_lines_filter(tmp_path):
    """Test filtering files by minimum line count."""
    file_1 = tmp_path / "1line.txt"
    file_1.write_text("line 1\n", encoding='utf-8')

    file_3 = tmp_path / "3lines.txt"
    file_3.write_text("line 1\nline 2\nline 3\n", encoding='utf-8')

    filter_opts = {'min_lines': 2}
    search_opts = {}

    # 1 line file should be excluded
    included, reason = should_include(file_1, Path("1line.txt"), filter_opts, search_opts, return_reason=True)
    assert not included
    assert reason == 'too_few_lines'

    # 3 lines file should be included
    included, reason = should_include(file_3, Path("3lines.txt"), filter_opts, search_opts, return_reason=True)
    assert included

def test_max_lines_filter(tmp_path):
    """Test filtering files by maximum line count."""
    file_3 = tmp_path / "3lines.txt"
    file_3.write_text("line 1\nline 2\nline 3\n", encoding='utf-8')

    file_5 = tmp_path / "5lines.txt"
    file_5.write_text("1\n2\n3\n4\n5\n", encoding='utf-8')

    filter_opts = {'max_lines': 4}
    search_opts = {}

    # 3 lines file should be included
    included, reason = should_include(file_3, Path("3lines.txt"), filter_opts, search_opts, return_reason=True)
    assert included

    # 5 lines file should be excluded
    included, reason = should_include(file_5, Path("5lines.txt"), filter_opts, search_opts, return_reason=True)
    assert not included
    assert reason == 'too_many_lines'

def test_min_max_lines_combined(tmp_path):
    """Test filtering files by both minimum and maximum line count."""
    file_1 = tmp_path / "1line.txt"
    file_1.write_text("1\n", encoding='utf-8')

    file_3 = tmp_path / "3lines.txt"
    file_3.write_text("1\n2\n3\n", encoding='utf-8')

    file_5 = tmp_path / "5lines.txt"
    file_5.write_text("1\n2\n3\n4\n5\n", encoding='utf-8')

    filter_opts = {'min_lines': 2, 'max_lines': 4}
    search_opts = {}

    assert not should_include(file_1, Path("1line.txt"), filter_opts, search_opts)
    assert should_include(file_3, Path("3lines.txt"), filter_opts, search_opts)
    assert not should_include(file_5, Path("5lines.txt"), filter_opts, search_opts)

def test_virtual_content_line_filter():
    """Test line-count filtering for virtual content (used in extraction)."""
    content_3 = "1\n2\n3\n"
    content_5 = "1\n2\n3\n4\n5\n"

    filter_opts = {'max_lines': 4}
    search_opts = {}

    # Content with 3 lines should be included
    included, reason = should_include(None, Path("virtual.txt"), filter_opts, search_opts, virtual_content=content_3, return_reason=True)
    assert included

    # Content with 5 lines should be excluded
    included, reason = should_include(None, Path("virtual.txt"), filter_opts, search_opts, virtual_content=content_5, return_reason=True)
    assert not included
    assert reason == 'too_many_lines'

def test_line_filter_validation():
    """Test that min_lines and max_lines validation works in utils.py."""
    import copy
    from utils import validate_config, DEFAULT_CONFIG, InvalidConfigError

    config = copy.deepcopy(DEFAULT_CONFIG)

    # Valid
    config['filters']['min_lines'] = 10
    config['filters']['max_lines'] = 20
    validate_config(config)

    # Invalid: Negative min_lines
    config['filters']['min_lines'] = -1
    with pytest.raises(InvalidConfigError, match="filters.min_lines must be 0 or more"):
        validate_config(config)

    # Invalid: Negative max_lines
    config['filters']['min_lines'] = 0
    config['filters']['max_lines'] = -5
    with pytest.raises(InvalidConfigError, match="filters.max_lines must be 0 or more"):
        validate_config(config)
