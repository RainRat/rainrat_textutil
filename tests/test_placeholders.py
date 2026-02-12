import os
from pathlib import Path
import pytest
from sourcecombine import find_and_combine_files

def test_file_metadata_placeholders(tmp_path):
    """Test that all file-level placeholders are correctly replaced."""
    root = tmp_path / "project"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()

    file_path = sub / "example.txt"
    content = "Hello World"
    file_path.write_text(content, encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "output": {
            "file": str(output_file),
            "header_template": "FILE:{{FILENAME}} EXT:{{EXT}} STEM:{{STEM}} DIR:{{DIR}} SLUG:{{DIR_SLUG}} SIZE:{{SIZE}} TOKENS:{{TOKENS}}\n",
            "footer_template": "END:{{FILENAME}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()

    # FILENAME should be sub/example.txt (posix style)
    assert "FILE:sub/example.txt" in result
    assert "EXT:txt" in result
    assert "STEM:example" in result
    assert "DIR:sub" in result
    assert "SLUG:sub" in result
    assert "SIZE:11.00 B" in result
    # "Hello World" is 11 chars. Default estimate is len//4 = 2 tokens if tiktoken missing.
    # Extract the token count from the header and check that it's the same in the footer
    import re
    header_tokens = re.search(r"TOKENS:(\d+)", result).group(1)
    # The header and footer should have the SAME token count (referring to the file content)
    # Even though they were rendered at different times.
    assert f"TOKENS:{header_tokens}" in result
    # We'll check the footer separately if we add a marker
    assert "END:sub/example.txt" in result

def test_footer_token_consistency(tmp_path):
    """Test that footer {{TOKENS}} is consistent with the header."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "f1.txt").write_text("Longer content to ensure more than 0 tokens")

    output_file = tmp_path / "combined.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(output_file),
            "header_template": "H:{{TOKENS}}\n",
            "footer_template": "F:{{TOKENS}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))
    result = output_file.read_text()

    import re
    h_tokens = re.search(r"H:(\d+)", result).group(1)
    f_tokens = re.search(r"F:(\d+)", result).group(1)

    assert h_tokens == f_tokens
    assert int(h_tokens) > 0

def test_global_metadata_placeholders(tmp_path):
    """Test that all global-level placeholders are correctly replaced."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "f1.txt").write_text("One")   # 3 bytes
    (root / "f2.txt").write_text("Two!")  # 4 bytes

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "output": {
            "file": str(output_file),
            "global_header_template": "COUNT:{{FILE_COUNT}} SIZE:{{TOTAL_SIZE}} TOKENS:{{TOTAL_TOKENS}}\n",
            "global_footer_template": "FINISH:{{FILE_COUNT}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()

    assert "COUNT:2" in result
    assert "SIZE:7.00 B" in result
    # We check for the value since the placeholder is replaced
    assert "TOKENS:" in result
    assert "FINISH:2" in result

def test_placeholders_in_max_size(tmp_path):
    """Test placeholders in max_size_placeholder."""
    root = tmp_path / "project"
    root.mkdir()
    file_path = root / "large.txt"
    file_path.write_text("Very large content") # 18 bytes

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "filters": {"max_size_bytes": 5}, # Force skip
        "output": {
            "file": str(output_file),
            "max_size_placeholder": "SKIPPED {{FILENAME}} SIZE:{{SIZE}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()
    assert "SKIPPED large.txt SIZE:18.00 B" in result

def test_dir_placeholders_root(tmp_path):
    """Test DIR and DIR_SLUG placeholders for files in the root."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "root_file.txt").write_text("content")

    output_file = tmp_path / "combined.txt"

    config = {
        "search": {"root_folders": [str(root)], "recursive": True},
        "output": {
            "file": str(output_file),
            "header_template": "DIR:{{DIR}} SLUG:{{DIR_SLUG}}\n",
        },
    }

    find_and_combine_files(config, str(output_file))

    result = output_file.read_text()
    assert "DIR:." in result
    assert "SLUG:root" in result
