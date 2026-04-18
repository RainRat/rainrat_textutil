from pathlib import Path
from sourcecombine import find_and_combine_files

def test_sort_by_lines_with_size_exclusion_robust(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    # Large file: 1 long line, but exceeds size limit
    # Lines: 1, Size: 1000 bytes
    large_file = root / "large.txt"
    large_file.write_text("A" * 1000, encoding="utf-8")

    # Small file: 5 lines, fits in size limit
    # Lines: 5, Size: ~30 bytes
    small_file = root / "small.txt"
    small_file.write_text("line1\nline2\nline3\nline4\nline5", encoding="utf-8")

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {
            "max_size_bytes": 100
        },
        "output": {
            "file": str(out_file),
            "sort_by": "lines",
            "max_size_placeholder": "L1\nL2\nL3\nL4\nL5\nL6\nL7\nL8\nL9\nL10", # 10 lines
            "header_template": "FILE: {{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    # If using original metrics: large.txt (1) < small.txt (5)
    # If using placeholder metrics: small.txt (5) < large.txt (10)
    # The code SHOULD use placeholder metrics for excluded files.

    find_and_combine_files(config, str(out_file))

    content = out_file.read_text(encoding="utf-8")

    pos_small = content.find("FILE: small.txt")
    pos_large = content.find("FILE: large.txt")

    # We expect small.txt (5 lines) to come before large.txt (replaced by 10-line placeholder)
    assert pos_small != -1
    assert pos_large != -1
    assert pos_small < pos_large

def test_sort_by_lines_with_size_exclusion_reverse_robust(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    large_file = root / "large.txt"
    large_file.write_text("A" * 1000, encoding="utf-8")

    small_file = root / "small.txt"
    small_file.write_text("line1\nline2\nline3\nline4\nline5", encoding="utf-8")

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {
            "max_size_bytes": 100
        },
        "output": {
            "file": str(out_file),
            "sort_by": "lines",
            "sort_reverse": True,
            "max_size_placeholder": "L1\nL2\nL3\nL4\nL5\nL6\nL7\nL8\nL9\nL10", # 10 lines
            "header_template": "FILE: {{FILENAME}}\n",
            "footer_template": "\n"
        }
    }

    # Reverse sort: large.txt (10) > small.txt (5)

    find_and_combine_files(config, str(out_file))

    content = out_file.read_text(encoding="utf-8")

    pos_small = content.find("FILE: small.txt")
    pos_large = content.find("FILE: large.txt")

    assert pos_small != -1
    assert pos_large != -1
    assert pos_large < pos_small
