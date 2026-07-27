import sys
import os
from pathlib import Path
from unittest.mock import patch
import logging
import pytest
import json

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import main, _progress_enabled, verify_files

@pytest.fixture
def temp_cwd(tmp_path):
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)

@pytest.fixture
def mock_argv():
    def _mock_argv(args):
        return patch.object(sys, 'argv', ['sourcecombine.py'] + args)
    return _mock_argv

def test_quiet_flag_suppresses_logging_and_summary(temp_cwd, mock_argv, caplog, capsys):
    dummy_file = temp_cwd / "dummy.txt"
    dummy_file.write_text("Hello World", encoding="utf-8")

    with mock_argv(['-q', '--dry-run']):
        main()

    assert logging.getLogger().getEffectiveLevel() == logging.WARNING

    info_messages = [r.message for r in caplog.records if r.levelno < logging.WARNING]
    assert len(info_messages) == 0

    captured = capsys.readouterr()
    assert "=== COMBINE" not in captured.err
    assert "Files" not in captured.err

def test_quiet_flag_disables_progress_bar():
    original_level = logging.getLogger().getEffectiveLevel()
    logging.getLogger().setLevel(logging.WARNING)
    try:
        assert _progress_enabled(dry_run=False) is False
    finally:
        logging.getLogger().setLevel(original_level)

def test_quiet_verify_suppresses_successful_and_skipped_entries(temp_cwd, mock_argv, capsys):
    test_file = temp_cwd / "a.txt"
    test_file.write_text("content", encoding="utf-8")

    manifest = [
        {
            "path": "a.txt",
            "content": "content",
            "size_bytes": 7,
            "sha256": "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73"
        }
    ]
    manifest_file = temp_cwd / "combined_files.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    with mock_argv(['--verify', 'combined_files.json', '-q']):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    captured = capsys.readouterr()
    assert "[OK]" not in captured.out
    assert "Summary:" not in captured.out
    assert "Matches:" not in captured.out

def test_quiet_verify_still_reports_mismatches_and_failures(temp_cwd, mock_argv, capsys):
    test_file = temp_cwd / "a.txt"
    test_file.write_text("wrong content", encoding="utf-8")

    manifest = [
        {
            "path": "a.txt",
            "content": "content",
            "size_bytes": 7,
            "sha256": "ed7002b439e9ac845f22357d822bac1444730fbdb6016d3ec9432297b9ec9f73"
        }
    ]
    manifest_file = temp_cwd / "combined_files.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    with mock_argv(['--verify', 'combined_files.json', '-q']):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    captured = capsys.readouterr()
    assert "[MISMATCH]" in captured.out or "[ERROR]" in captured.out
    assert "[OK]" not in captured.out
    assert "Summary:" in captured.out
    assert "Mismatches: 1" in captured.out
