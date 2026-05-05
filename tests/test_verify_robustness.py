import json
import logging
import pytest
import hashlib
from pathlib import Path
from unittest.mock import patch
from sourcecombine import verify_files

def test_verify_no_files_found(caplog):
    """Cover lines 4494, 4498-4499: No files found to verify."""
    sources = [("empty.txt", "just some text without headers")]
    with caplog.at_level(logging.WARNING):
        with pytest.raises(SystemExit) as exc:
            verify_files(sources)
    assert exc.value.code == 1
    assert "No files found to verify in empty.txt" in caplog.text
    assert "No files found to verify in any of the sources" in caplog.text

def test_verify_unsafe_paths(tmp_path, caplog):
    """Cover lines 4513-4514: Skipping unsafe paths."""
    manifest = [
        {"path": "/abs/path.txt", "content": "data"},
        {"path": "../traversal.txt", "content": "data"},
        {"path": "C:\\windows.txt", "content": "data"},
    ]
    sources = [("manifest.json", json.dumps(manifest))]

    with caplog.at_level(logging.WARNING):
        results = verify_files(sources, root_folder=tmp_path)

    assert "Skipping unsafe path: /abs/path.txt" in caplog.text
    assert "Skipping unsafe path: ../traversal.txt" in caplog.text
    # Total is 3, but all 3 are skipped in the loop before reaching status increment
    # Wait, the code says 'continue', so they don't count towards matches/mismatches/missing
    assert results['total'] == 3
    assert results['matches'] == 0
    assert results['mismatches'] == 0
    assert results['missing'] == 0

def test_verify_hash_mismatch_with_diff(tmp_path, capsys):
    """Cover lines 4537-4538: Hash mismatch showing diff."""
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "test.txt"
    file1.write_text("actual", encoding="utf-8")

    # Manifest has different hash AND expected content
    expected_content = "expected"
    wrong_sha = hashlib.sha256(b"wrong").hexdigest()

    manifest = [{"path": "test.txt", "sha256": wrong_sha, "content": expected_content}]
    sources = [("manifest.json", json.dumps(manifest))]

    # Run with show_diff=True
    verify_files(sources, root_folder=root, show_diff=True)

    out, err = capsys.readouterr()
    assert "[MISMATCH]" in out
    assert "(hash mismatch)" in out
    # Diff goes to stderr
    assert "--- a/test.txt" in err
    assert "-actual" in err
    assert "+expected" in err

def test_verify_invalid_paths(tmp_path, caplog):
    """Cover lines 4516-4518: Skipping invalid paths."""
    # We can trigger ValueError in Path if it contains null bytes
    manifest = [
        {"path": "invalid\0path.txt", "content": "data"}
    ]
    sources = [("manifest.json", json.dumps(manifest))]

    with caplog.at_level(logging.WARNING):
        results = verify_files(sources, root_folder=tmp_path)

    assert "Skipping invalid path" in caplog.text
    assert results['total'] == 1

def test_verify_file_access_error(tmp_path, capsys):
    """Cover lines 4539-4541: OSError during file read for hash check."""
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "protected.txt"
    file1.write_text("secret", encoding="utf-8")
    sha1 = hashlib.sha256(b"secret").hexdigest()

    manifest = [{"path": "protected.txt", "sha256": sha1}]
    sources = [("manifest.json", json.dumps(manifest))]

    # Mock read_bytes to raise OSError
    with patch("pathlib.Path.read_bytes", side_effect=OSError("Permission denied")):
        results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[ERROR]" in out
    assert "Permission denied" in out
    assert results['mismatches'] == 1

def test_verify_skipped_entry(tmp_path, capsys):
    """Cover line 4558: Entry with neither hash nor content."""
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "exists.txt"
    file1.write_text("content", encoding="utf-8")

    # JSON entry with path only
    manifest = [{"path": "exists.txt"}]
    sources = [("manifest.json", json.dumps(manifest))]

    results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[SKIPPED]" in out
    assert "no hash or content to verify against" in out
    assert results['matches'] == 0
    assert results['mismatches'] == 0
    assert results['missing'] == 0
