import pytest
from pathlib import Path
from sourcecombine import find_and_combine_files, should_include
import utils

def test_summary_breakdown_reasons(tmp_path):
    # Create a test environment
    root = tmp_path / "project"
    root.mkdir()
    (root / "include.txt").write_text("content")
    (root / "exclude.txt").write_text("content")
    (root / "too_small.txt").write_text("a")
    (root / "binary.bin").write_bytes(b"\x00\x01\x02")

    sub = root / "ignored_folder"
    sub.mkdir()
    (sub / "file.txt").write_text("content")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(root)], 'recursive': True}
    config['filters'] = {
        'min_size_bytes': 5,
        'skip_binary': True,
        'exclusions': {
            'filenames': ['exclude.txt'],
            'folders': ['ignored_folder']
        }
    }

    stats = find_and_combine_files(config, str(tmp_path / "out.txt"), dry_run=True)

    reasons = stats['filter_reasons']
    assert reasons.get('excluded') == 1  # exclude.txt
    assert reasons.get('too_small') == 1  # too_small.txt
    assert reasons.get('binary') == 1  # binary.bin
    assert reasons.get('excluded_folder') == 1  # ignored_folder

def test_budget_limit_reason(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "file1.txt").write_text("content 1")
    (root / "file2.txt").write_text("content 2")
    (root / "file3.txt").write_text("content 3")

    config = utils.DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(root)]}
    config['filters'] = {
        'max_total_tokens': 5  # Very small budget
    }

    stats = find_and_combine_files(config, str(tmp_path / "out.txt"))

    assert stats['budget_exceeded'] is True
    assert stats['filter_reasons'].get('budget_limit', 0) > 0
