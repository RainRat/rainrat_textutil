import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import time
import pytest
import logging
from io import StringIO
from contextlib import contextmanager
from sourcecombine import find_and_combine_files, extract_files

@contextmanager
def log_capture():
    """Context manager to capture log output."""
    log_stream = StringIO()
    logger = logging.getLogger()
    old_level = logger.level
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(log_stream)
    logger.addHandler(handler)
    try:
        yield log_stream
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)

@pytest.fixture
def test_env(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    # Create files with different number of lines
    (root / "1line.txt").write_text("one line", encoding="utf-8")
    (root / "3lines.txt").write_text("one\ntwo\nthree", encoding="utf-8")
    (root / "2lines.txt").write_text("one\ntwo", encoding="utf-8")

    return root, tmp_path

def test_sort_by_lines_combining(test_env):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "lines",
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    # Sorted by lines: 1line.txt, 2lines.txt, 3lines.txt
    assert lines == ["1line.txt", "2lines.txt", "3lines.txt"]

def test_sort_by_lines_reverse_combining(test_env):
    root, tmp_path = test_env
    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "output": {
            "file": str(out_file),
            "sort_by": "lines",
            "sort_reverse": True,
            "header_template": "{{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    find_and_combine_files(config, str(out_file))
    content = out_file.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip().endswith(".txt")]
    # Sorted by lines reverse: 3lines.txt, 2lines.txt, 1line.txt
    assert lines == ["3lines.txt", "2lines.txt", "1line.txt"]

def test_sort_by_lines_extraction(tmp_path):
    # Create a combined JSON content
    # We use names that would be in different order alphabetically
    combined_json = """
    [
      {"path": "a_3lines.txt", "content": "one\\ntwo\\nthree"},
      {"path": "b_1line.txt", "content": "one line"},
      {"path": "c_2lines.txt", "content": "one\\ntwo"}
    ]
    """

    out_dir = tmp_path / "extracted"
    out_dir.mkdir()

    with log_capture() as log_stream:
        # Alphabetical: a, b, c
        # By lines: b(1), c(2), a(3)
        extract_files([("input.json", combined_json)], out_dir, sort_by="lines")
        log_output = log_stream.getvalue()

        # Check order in logs
        pos_a = log_output.find("Extracted: " + str(out_dir / "a_3lines.txt"))
        pos_b = log_output.find("Extracted: " + str(out_dir / "b_1line.txt"))
        pos_c = log_output.find("Extracted: " + str(out_dir / "c_2lines.txt"))

        assert pos_a != -1 and pos_b != -1 and pos_c != -1
        assert pos_b < pos_c < pos_a

def test_pairing_sort_by_lines(test_env):
    root, tmp_path = test_env
    # Create pairs with different line counts
    (root / "file1.cpp").write_text("one\ntwo", encoding="utf-8") # 2 lines
    (root / "file1.h").write_text("hdr1", encoding="utf-8")
    (root / "file2.cpp").write_text("one", encoding="utf-8") # 1 line
    (root / "file2.h").write_text("hdr2", encoding="utf-8")

    out_dir = tmp_path / "paired_lines"
    config = {
        "search": {"root_folders": [str(root)]},
        "pairing": {
            "enabled": True,
            "source_extensions": [".cpp"],
            "header_extensions": [".h"]
        },
        "output": {
            "folder": str(out_dir),
            "sort_by": "lines",
            "paired_filename_template": "{{STEM}}.combined"
        }
    }

    with log_capture() as log_stream:
        find_and_combine_files(config, str(out_dir), dry_run=True)
        log_output = log_stream.getvalue()
        # file2 (1 line) should appear before file1 (2 lines)
        pos1 = log_output.find("[PAIR file1]")
        pos2 = log_output.find("[PAIR file2]")
        assert pos1 != -1
        assert pos2 != -1
        assert pos2 < pos1
