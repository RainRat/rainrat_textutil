import os
import json
import hashlib
import argparse
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from sourcecombine import (
    _format_information_summary,
    verify_files,
    _print_execution_summary,
    C_GREEN, C_YELLOW, C_RED, C_RESET
)

def test_format_information_summary_colored_status():
    """Test _format_information_summary with colored=True for various statuses."""
    with patch('sys.stderr.isatty', return_value=True), \
         patch('sys.stdout.isatty', return_value=True), \
         patch.dict(os.environ, {}, clear=False):
        if "NO_COLOR" in os.environ:
            del os.environ["NO_COLOR"]

        # Test 'A' (Added)
        meta_a = {'status': 'A'}
        summary_a = _format_information_summary(meta_a, colored=True)
        assert "\033[32m[A]\033[0m" in summary_a

        # Test '??' (Untracked)
        meta_u = {'status': '??'}
        summary_u = _format_information_summary(meta_u, colored=True)
        assert "\033[32m[??]\033[0m" in summary_u

        # Test 'M' (Modified)
        meta_m = {'status': 'M'}
        summary_m = _format_information_summary(meta_m, colored=True)
        assert "\033[33m[M]\033[0m" in summary_m

        # Test 'R' (Renamed)
        meta_r = {'status': 'R'}
        summary_r = _format_information_summary(meta_r, colored=True)
        assert "\033[33m[R]\033[0m" in summary_r

        # Test 'D' (Deleted)
        meta_d = {'status': 'D'}
        summary_d = _format_information_summary(meta_d, colored=True)
        assert "\033[31m[D]\033[0m" in summary_d

        # Test unknown status
        meta_x = {'status': 'X'}
        summary_x = _format_information_summary(meta_x, colored=True)
        assert "[X]" in summary_x
        # It should NOT have color codes if it's unknown
        assert "\033[" not in summary_x

def test_verify_repair_missing_with_mtime(tmp_path):
    """Test verify_files repair of missing file with modification time."""
    root = tmp_path / "root"
    root.mkdir()

    mtime = 123456789.0
    combined_data = [
        {
            "path": "missing.txt",
            "content": "new content",
            "modified": mtime
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 1
    target = root / "missing.txt"
    assert target.exists()
    # Path.stat().st_mtime might have slight precision differences on some systems,
    # but usually it should match or be very close.
    assert abs(target.stat().st_mtime - mtime) < 0.1

def test_verify_repair_missing_oserror(tmp_path):
    """Test verify_files repair of missing file handles OSError during write."""
    root = tmp_path / "root"
    root.mkdir()

    combined_data = [
        {
            "path": "missing.txt",
            "content": "new content"
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    # Mock Path.write_text to raise OSError
    with patch.object(Path, 'write_text', side_effect=OSError("Disk full")):
        results = verify_files(sources, root_folder=root, repair=True)
        assert results['missing'] == 1
        assert results['repaired'] == 0

def test_verify_repair_hash_mismatch_dry_run(tmp_path):
    """Test verify_files repair of hash mismatch in dry_run mode."""
    root = tmp_path / "root"
    root.mkdir()

    file_path = root / "mismatch.txt"
    file_path.write_text("old content")

    expected_content = "new content"
    expected_sha = hashlib.sha256(expected_content.encode()).hexdigest()

    combined_data = [
        {
            "path": "mismatch.txt",
            "content": expected_content,
            "sha256": expected_sha
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    results = verify_files(sources, root_folder=root, repair=True, dry_run=True)
    assert results['repaired'] == 1
    assert file_path.read_text() == "old content"

def test_verify_repair_hash_mismatch_success(tmp_path):
    """Test verify_files repair of hash mismatch successfully."""
    root = tmp_path / "root"
    root.mkdir()

    file_path = root / "mismatch.txt"
    file_path.write_text("old content")

    mtime = 1122334455.0
    expected_content = "new content"
    expected_sha = hashlib.sha256(expected_content.encode()).hexdigest()

    combined_data = [
        {
            "path": "mismatch.txt",
            "content": expected_content,
            "sha256": expected_sha,
            "modified": mtime
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 1
    assert file_path.read_text() == "new content"
    assert abs(file_path.stat().st_mtime - mtime) < 0.1

def test_verify_repair_hash_mismatch_oserror(tmp_path):
    """Test verify_files repair of hash mismatch handles OSError during repair."""
    root = tmp_path / "root"
    root.mkdir()

    file_path = root / "mismatch.txt"
    file_path.write_text("old content")

    expected_content = "new content"
    expected_sha = hashlib.sha256(expected_content.encode()).hexdigest()

    combined_data = [
        {
            "path": "mismatch.txt",
            "content": expected_content,
            "sha256": expected_sha
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    with patch.object(Path, 'write_text', side_effect=OSError("Permission denied")):
        results = verify_files(sources, root_folder=root, repair=True)
        assert results['mismatches'] == 1
        assert results['repaired'] == 0

def test_verify_repair_content_mismatch_dry_run(tmp_path):
    """Test verify_files repair of content mismatch in dry_run mode."""
    root = tmp_path / "root"
    root.mkdir()

    file_path = root / "mismatch.txt"
    file_path.write_text("old content")

    combined_data = [
        {
            "path": "mismatch.txt",
            "content": "new content"
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    results = verify_files(sources, root_folder=root, repair=True, dry_run=True)
    assert results['repaired'] == 1
    assert file_path.read_text() == "old content"

def test_verify_repair_content_mismatch_with_mtime(tmp_path):
    """Test verify_files repair of content mismatch with modification time."""
    root = tmp_path / "root"
    root.mkdir()

    file_path = root / "mismatch.txt"
    file_path.write_text("old content")

    mtime = 987654321.0
    combined_data = [
        {
            "path": "mismatch.txt",
            "content": "new content",
            "modified": mtime
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    results = verify_files(sources, root_folder=root, repair=True)
    assert results['repaired'] == 1
    assert file_path.read_text() == "new content"
    assert abs(file_path.stat().st_mtime - mtime) < 0.1

def test_verify_repair_content_mismatch_oserror(tmp_path):
    """Test verify_files repair of content mismatch handles OSError during repair."""
    root = tmp_path / "root"
    root.mkdir()

    file_path = root / "mismatch.txt"
    file_path.write_text("old content")

    combined_data = [
        {
            "path": "mismatch.txt",
            "content": "new content"
        }
    ]
    sources = [("test.json", json.dumps(combined_data))]

    with patch.object(Path, 'write_text', side_effect=OSError("Read-only file system")):
        results = verify_files(sources, root_folder=root, repair=True)
        assert results['mismatches'] == 1
        assert results['repaired'] == 0

def test_print_execution_summary_with_status():
    """Test _print_execution_summary displays status in Largest Files table."""
    stats = {
        'total_files': 1,
        'total_size_bytes': 100,
        'total_tokens': 10,
        'total_lines': 5,
        'top_files': [(10, 100, 'test.py', 'M')],
        'files_by_language': {'.py': 1},
        'tokens_by_language': {'.py': 10},
        'size_by_language': {'.py': 100},
        'project_name': 'TestProj',
        'git_branch': 'main',
        'git_commit_short': 'abc1234'
    }
    args = argparse.Namespace(
        dry_run=False,
        estimate_tokens=False,
        list_files=False,
        tree=False,
        extract=False,
        apply_in_place=False,
        format='text'
    )

    with patch('sys.stderr', new_callable=MagicMock) as mock_stderr, \
         patch('shutil.get_terminal_size', return_value=MagicMock(columns=120)):
        # We need isatty to be true to trigger colored output if we want to see it,
        # but here we just want to ensure it doesn't crash and includes status.
        mock_stderr.isatty.return_value = True
        _print_execution_summary(stats, args, pairing_enabled=False)

        # Check if [M] or similar indicator was written to stderr
        all_calls = "".join(call.args[0] for call in mock_stderr.write.call_args_list)
        assert "[M]" in all_calls
