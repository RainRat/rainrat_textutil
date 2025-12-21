import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import find_and_combine_files, InvalidConfigError

def test_paired_filename_template_invalid_placeholder(tmp_path):
    # Test that using a single-brace placeholder that is not in the allowed list triggers ValueError
    # This specifically targets the KeyError catch block in _render_paired_filename
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    hdr = root / "file.h"
    src.write_text("source", encoding="utf-8")
    hdr.write_text("header", encoding="utf-8")

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
            "paired_filename_template": "{UNKNOWN}_file.txt"
        }
    }

    # The KeyError is caught and re-raised as ValueError
    with pytest.raises(ValueError, match="Missing value for placeholder '{{UNKNOWN}}'"):
        find_and_combine_files(config, str(output_dir))


def test_paired_filename_template_double_brace_unknown(tmp_path):
    # Test that using a double-brace placeholder that is not in the allowed list triggers ValueError
    # This targets the _to_format_placeholder validation check
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    hdr = root / "file.h"
    src.write_text("source", encoding="utf-8")
    hdr.write_text("header", encoding="utf-8")

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
            "paired_filename_template": "{{UNKNOWN}}_file.txt"
        }
    }

    with pytest.raises(ValueError, match="Unknown placeholder '{{UNKNOWN}}'"):
        find_and_combine_files(config, str(output_dir))


def test_paired_filename_template_absolute_path(tmp_path):
    # Test that if the template results in an absolute path, InvalidConfigError is raised
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    hdr = root / "file.h"
    src.write_text("source", encoding="utf-8")
    hdr.write_text("header", encoding="utf-8")

    output_dir = tmp_path / "output"

    # Construct an absolute path template
    # We use a leading slash (or drive letter on Windows) to simulate absolute path
    absolute_template = "/tmp/abs/{{STEM}}.txt"
    if os.name == 'nt':
        absolute_template = "C:/tmp/abs/{{STEM}}.txt"

    config = {
        "search": {"root_folders": [str(root)]},
        "pairing": {
            "enabled": True,
            "source_extensions": [".cpp"],
            "header_extensions": [".h"]
        },
        "output": {
            "folder": str(output_dir),
            "paired_filename_template": absolute_template
        }
    }

    with pytest.raises(InvalidConfigError, match="Paired filename template must produce a relative path"):
        find_and_combine_files(config, str(output_dir))
