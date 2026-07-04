import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import sourcecombine
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

def test_folder_redundancy_filtering(monkeypatch, capsys):
    """Verify that redundant parent folders are filtered from the summary."""
    # Mock stats where a deep folder has the same stats as its parents
    # very/long/path/file.py
    stats = {
        'total_files': 1,
        'total_discovered': 1,
        'total_size_bytes': 1000,
        'total_tokens': 100,
        'total_lines': 10,
        'token_count_is_approx': False,
        'files_by_language': {'python': 1},
        'tokens_by_language': {'python': 100},
        'project_name': 'TestProject',
        'top_files': [
            (100, 1000, "very/long/path/file.py", None, 10, "python"),
        ]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False
    args.extract = False
    args.format = 'text'

    # Force NO_COLOR
    monkeypatch.setenv("NO_COLOR", "1")

    # Mock terminal width
    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=80)):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err
    lines = stderr.splitlines()

    # Identify lines in Largest Folders section
    in_folders = False
    folder_entries = []
    for line in lines:
        if "Largest Folders" in line:
            in_folders = True
            continue
        if in_folders:
            if not line.strip() or "Languages" in line or "====" in line:
                in_folders = False
                continue
            if "FOLDER" in line:
                continue
            folder_entries.append(line.strip())

    # Should only have one folder entry: the most specific one
    assert len(folder_entries) == 1
    assert folder_entries[0].endswith("very/long/path/")

def test_folder_diversity_preserved(monkeypatch, capsys):
    """Verify that diverse folders are NOT filtered out."""
    # Mock stats where folders have different file counts/stats
    # folder1/file1.py
    # folder1/sub/file2.py
    stats = {
        'total_files': 2,
        'total_discovered': 2,
        'total_size_bytes': 2000,
        'total_tokens': 200,
        'total_lines': 20,
        'token_count_is_approx': False,
        'files_by_language': {'python': 2},
        'tokens_by_language': {'python': 200},
        'project_name': 'TestProject',
        'top_files': [
            (100, 1000, "folder1/file1.py", None, 10, "python"),
            (100, 1000, "folder1/sub/file2.py", None, 10, "python"),
        ]
    }

    # Mock args
    args = MagicMock()
    args.dry_run = False
    args.estimate_tokens = True
    args.list_files = False
    args.tree = False
    args.extract = False
    args.format = 'text'

    # Force NO_COLOR
    monkeypatch.setenv("NO_COLOR", "1")

    # Mock terminal width
    with patch('shutil.get_terminal_size', return_value=MagicMock(columns=100)):
        sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

    captured = capsys.readouterr()
    stderr = captured.err

    # folder1/ contains 2 files, folder1/sub/ contains 1 file.
    # Statistics are different, so both should be shown.
    assert "folder1/" in stderr
    assert "folder1/sub/" in stderr
