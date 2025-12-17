import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files

def test_find_and_combine_files_pairing_integration(tmp_path):
    # Setup
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    hdr = root / "file.h"
    src.write_text("source code", encoding="utf-8")
    hdr.write_text("header code", encoding="utf-8")

    output_dir = tmp_path / "output"

    config = {
        "search": {"root_folders": [str(root)]},
        "pairing": {
            "enabled": True,
            "source_extensions": [".cpp"],
            "header_extensions": [".h"]
        },
        "output": {
            "folder": str(output_dir),
            # default template is {{STEM}}.combined
        }
    }

    find_and_combine_files(config, str(output_dir))

    expected_file = output_dir / "file.combined"
    assert expected_file.exists()
    content = expected_file.read_text(encoding="utf-8")
    assert "source code" in content
    assert "header code" in content


def test_find_and_combine_files_pairing_with_size_exclusion(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    hdr = root / "file.h"
    src.write_text("small", encoding="utf-8")
    # Create a large file
    hdr.write_text("large" * 100, encoding="utf-8")

    output_dir = tmp_path / "output"

    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {
            "max_size_bytes": 50 # "large"*100 > 50
        },
        "pairing": {
            "enabled": True,
            "source_extensions": [".cpp"],
            "header_extensions": [".h"]
        },
        "output": {
            "folder": str(output_dir),
            "max_size_placeholder": "SKIPPED {{FILENAME}}",
            "header_template": "",
            "footer_template": ""
        }
    }

    find_and_combine_files(config, str(output_dir))

    expected_file = output_dir / "file.combined"
    assert expected_file.exists()
    content = expected_file.read_text(encoding="utf-8")
    assert "small" in content
    # hdr should be skipped
    # The filename in placeholder is relative to root path.
    # file.h is at root/file.h. relative to root is "file.h".
    assert "SKIPPED file.h" in content
