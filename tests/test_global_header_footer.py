import os
import sys
from pathlib import Path
import logging

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
from sourcecombine import find_and_combine_files

def test_global_header_and_footer(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    file1 = project_root / "file1.txt"
    file1.write_text("content1", encoding="utf-8")
    file2 = project_root / "file2.txt"
    file2.write_text("content2", encoding="utf-8")

    output_path = tmp_path / "out.txt"
    global_header = "--- GLOBAL HEADER ---\n"
    global_footer = "\n--- GLOBAL FOOTER ---"

    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "global_header_template": global_header,
            "global_footer_template": global_footer,
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    content = output_path.read_text(encoding="utf-8")

    # Check that header is at the beginning
    assert content.startswith(global_header)

    # Check that footer is at the end
    assert content.endswith(global_footer)

    # Check that content is present
    body = content[len(global_header):-len(global_footer)]
    assert "content1" in body
    assert "content2" in body

def test_global_header_only(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    file1 = project_root / "file1.txt"
    file1.write_text("content1", encoding="utf-8")

    output_path = tmp_path / "out.txt"
    global_header = "--- GLOBAL HEADER ---\n"

    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "global_header_template": global_header,
            "global_footer_template": None,
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith(global_header)
    assert "content1" in content

def test_global_footer_only(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    file1 = project_root / "file1.txt"
    file1.write_text("content1", encoding="utf-8")

    output_path = tmp_path / "out.txt"
    global_footer = "\n--- GLOBAL FOOTER ---"

    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "global_header_template": None,
            "global_footer_template": global_footer,
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    content = output_path.read_text(encoding="utf-8")
    assert content.endswith(global_footer)
    assert "content1" in content


def test_global_header_footer_across_multiple_roots(tmp_path):
    root_one = tmp_path / "proj1"
    root_two = tmp_path / "proj2"
    root_one.mkdir()
    root_two.mkdir()
    (root_one / "file1.txt").write_text("content1", encoding="utf-8")
    (root_two / "file2.txt").write_text("content2", encoding="utf-8")

    output_path = tmp_path / "out.txt"
    global_header = "--- GLOBAL HEADER ---\n"
    global_footer = "\n--- GLOBAL FOOTER ---"

    config = {
        "search": {
            "root_folders": [os.fspath(root_one), os.fspath(root_two)],
            "recursive": True,
        },
        "filters": {},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "global_header_template": global_header,
            "global_footer_template": global_footer,
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    content = output_path.read_text(encoding="utf-8")
    assert content.startswith(global_header)
    assert content.endswith(global_footer)
    assert content.count(global_header) == 1
    assert content.count(global_footer) == 1


def test_global_header_footer_dry_run(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    file1 = project_root / "file1.txt"
    file1.write_text("content1", encoding="utf-8")

    output_path = tmp_path / "out.txt"
    global_header = "--- GLOBAL HEADER ---\n"
    global_footer = "\n--- GLOBAL FOOTER ---"

    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "global_header_template": global_header,
            "global_footer_template": global_footer,
        },
    }

    stats = find_and_combine_files(config, output_path, dry_run=True)

    assert stats is not None
    assert stats.get("total_files") is not None
