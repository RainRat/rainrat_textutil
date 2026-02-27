import sys
import os
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
from sourcecombine import find_and_combine_files

def test_token_limit_enforcement(tmp_path, monkeypatch):
    """Verify that the token limit correctly truncates the file list."""
    root = tmp_path / "root"
    root.mkdir()
    # 1 token approx = 4 chars
    (root / "file1.txt").write_text("1234", encoding="utf-8") # 1 token
    (root / "file2.txt").write_text("5678", encoding="utf-8") # 1 token
    (root / "file3.txt").write_text("9012", encoding="utf-8") # 1 token

    # Force fallback mode for deterministic counts
    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)], "recursive": False},
        "filters": {"max_total_tokens": 2},
        "output": {
            "file": str(out_file),
            "header_template": None,
            "footer_template": None
        }
    }

    # Use relative paths for explicit_files as they will be resolved relative to CWD (tmp_path)
    explicit = [Path("root/file1.txt"), Path("root/file2.txt"), Path("root/file3.txt")]

    stats = find_and_combine_files(
        config,
        output_path=str(out_file),
        explicit_files=[tmp_path / p for p in explicit]
    )

    assert stats['total_files'] == 2
    assert stats['token_limit_reached'] is True

    content = out_file.read_text(encoding="utf-8")
    assert "1234" in content
    assert "5678" in content
    assert "9012" not in content

def test_token_limit_with_toc(tmp_path, monkeypatch):
    """Verify that the TOC only includes files that fit within the limit."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("1234", encoding="utf-8")
    (root / "file2.txt").write_text("5678", encoding="utf-8")

    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        # Limit enough for TOC (~24) + 1 file (1) but not 2 files
        "filters": {"max_total_tokens": 25},
        "output": {
            "file": str(out_file),
            "table_of_contents": True,
            "header_template": None,
            "footer_template": None
        }
    }

    explicit = [tmp_path / "root/file1.txt", tmp_path / "root/file2.txt"]

    stats = find_and_combine_files(
        config,
        output_path=str(out_file),
        explicit_files=explicit
    )

    assert stats['total_files'] == 1
    assert stats['token_limit_reached'] is True

    content = out_file.read_text(encoding="utf-8")
    assert "Table of Contents:" in content
    assert "file1.txt" in content
    assert "file2.txt" not in content

def test_token_limit_zero_means_unlimited(tmp_path, monkeypatch):
    """Verify that max_total_tokens=0 means no limit."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("1234", encoding="utf-8")
    (root / "file2.txt").write_text("5678", encoding="utf-8")

    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 0},
        "output": {"file": str(out_file)}
    }

    stats = find_and_combine_files(
        config,
        output_path=str(out_file)
    )

    assert stats['total_files'] == 2
    assert stats['token_limit_reached'] is False

def test_token_limit_large_first_file(tmp_path, monkeypatch):
    """Verify that if the first file exceeds the limit, it is still included if it is the only one."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "large.txt").write_text("12345678", encoding="utf-8") # 2 tokens

    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 1},
        "output": {"file": str(out_file)}
    }

    stats = find_and_combine_files(
        config,
        output_path=str(out_file)
    )

    assert stats['total_files'] == 1
    # Current implementation doesn't mark token_limit_reached if the FIRST file is what exceeds it
    # and there are no more files to process anyway.
    assert stats['token_limit_reached'] is False


def test_limit_pass_apply_in_place(tmp_path, monkeypatch):
    """Verify apply_in_place works during the limiting pass."""
    root = tmp_path / "root"
    root.mkdir()
    f1 = root / "f1.txt"
    f1.write_text("content   ", encoding="utf-8")  # 3 trailing spaces

    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 100},
        "processing": {"apply_in_place": True, "compact_whitespace": True},
        "output": {"file": str(out_file)},
    }

    find_and_combine_files(config, output_path=str(out_file))

    # Verify update in place
    assert f1.read_text(encoding="utf-8") == "content"
    # Verify backup
    assert (root / "f1.txt.bak").exists()


def test_limit_pass_global_footer(tmp_path, monkeypatch):
    """Verify global footer tokens are counted during limiting."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "f1.txt").write_text("1234", encoding="utf-8")  # 1 token

    monkeypatch.setattr(utils, "tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 1},  # Only enough for f1.txt *or* footer, not both
        "output": {
            "file": str(out_file),
            "global_footer_template": "abcd",  # Another 1 token
            "format": "text",
        },
    }

    stats = find_and_combine_files(config, output_path=str(out_file))

    assert stats["token_limit_reached"] is True
