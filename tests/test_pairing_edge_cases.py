import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils

import os
import sys
from pathlib import Path

import pytest


from sourcecombine import find_and_combine_files



def test_paired_filename_template_collision(tmp_path):
    # Test that if the output file would overwrite an input file, it is skipped
    root = tmp_path / "project"
    root.mkdir()
    src = root / "file.cpp"
    src.write_text("source", encoding="utf-8")

    output_dir = tmp_path / "output"

    config = {
        "search": {"root_folders": [str(root)]},
        "pairing": {
            "enabled": True,
            "include_mismatched": True,
        },
        "output": {
            "folder": str(root), # Force output to input folder
            "paired_filename_template": "{{STEM}}.cpp" # Force collision
        }
    }

    # Should not raise, but should skip the file
    stats = find_and_combine_files(config, str(root))

    # Check that nothing was combined (total_tokens/size_bytes might be 0 or small due to headers)
    # Actually, if it's skipped, it shouldn't be in top_files
    assert not any(f[2].endswith("file.cpp") for f in stats.get('top_files', []))

    # Original file should still be original
    assert src.read_text(encoding="utf-8") == "source"


def test_paired_filename_template_double_brace_unknown(tmp_path):
    # Test that using a double-brace placeholder that is not in the allowed list triggers ValueError
    # This targets the validation loop in _render_paired_filename
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
    # Test that if the template results in an absolute path, utils.InvalidConfigError is raised
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

    with pytest.raises(utils.InvalidConfigError, match="Paired filename template must produce a relative path"):
        find_and_combine_files(config, str(output_dir))
