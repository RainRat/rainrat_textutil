import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files
from utils import DEFAULT_CONFIG
import copy

def test_pairing_stem_collision_with_mismatched(tmp_path):
    """
    Verify that a file with no extension (e.g. 'main') doesn't overwrite
    a paired group with the same stem (e.g. 'main.cpp', 'main.h')
    when include_mismatched is enabled.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.cpp").write_text("cpp content", encoding="utf-8")
    (src / "main.h").write_text("h content", encoding="utf-8")
    (src / "main").write_text("no extension content", encoding="utf-8")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config["search"]["root_folders"] = [str(src)]
    config["pairing"] = {
        "enabled": True,
        "source_extensions": [".cpp"],
        "header_extensions": [".h"],
        "include_mismatched": True
    }

    out_dir = tmp_path / "out"
    # find_and_combine_files will create out_dir if pairing is enabled
    stats = find_and_combine_files(config, str(out_dir))

    # We expect 2 output files:
    # 1. main.combined (from main.cpp and main.h)
    # 2. main (from the 'main' file with no extension)

    # If the bug is present, one might overwrite the other in the internal dict,
    # or they might both try to write to the same output file if templates collide.
    # But first, let's check how many files were processed.

    assert stats["total_files"] == 3

    combined_files = list(out_dir.glob("main.combined"))
    mismatched_files = list(out_dir.glob("main"))

    assert len(combined_files) == 1
    assert len(mismatched_files) == 1

    # Check content of main.combined
    combined_content = combined_files[0].read_text(encoding="utf-8")
    assert "cpp content" in combined_content
    assert "h content" in combined_content

    # Check content of the mismatched 'main'
    mismatched_content = mismatched_files[0].read_text(encoding="utf-8")
    assert "no extension content" in mismatched_content

def test_pairing_no_duplicates(tmp_path):
    """
    Verify that standard pairs are not duplicated in the output list.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.cpp").write_text("cpp", encoding="utf-8")
    (src / "main.h").write_text("h", encoding="utf-8")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config["search"]["root_folders"] = [str(src)]
    config["pairing"] = {
        "enabled": True,
        "source_extensions": [".cpp"],
        "header_extensions": [".h"],
        "include_mismatched": True
    }

    out_dir = tmp_path / "out"
    stats = find_and_combine_files(config, str(out_dir))

    # Should only have 1 combined file, and total files processed should be 2.
    assert stats["total_files"] == 2
    combined_files = list(out_dir.glob("*.combined"))
    assert len(combined_files) == 1
