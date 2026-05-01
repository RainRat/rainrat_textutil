import json
import hashlib
from pathlib import Path
import pytest
from sourcecombine import verify_files

def test_verify_match(tmp_path, capsys):
    # Setup files
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("hello world", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello world").hexdigest()

    # Manifest
    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello world"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Run verify
    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[OK]" in out
    assert "file1.txt" in out
    assert "hash match" in out
    assert results['matches'] == 1
    assert results['mismatches'] == 0
    assert results['missing'] == 0

def test_verify_mismatch(tmp_path, capsys):
    # Setup files
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("changed content", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello world").hexdigest() # Old hash

    # Manifest
    manifest = [
        {"path": "file1.txt", "sha256": sha1}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Run verify
    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[MISMATCH]" in out
    assert "hash mismatch" in out
    assert results['matches'] == 0
    assert results['mismatches'] == 1

def test_verify_missing(tmp_path, capsys):
    # Setup files
    root = tmp_path / "project"
    root.mkdir()
    # file1.txt is NOT created

    # Manifest
    manifest = [
        {"path": "file1.txt", "sha256": "somehash"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Run verify
    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[MISSING]" in out
    assert results['missing'] == 1

def test_verify_content_match_no_hash(tmp_path, capsys):
    # Setup files
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("hello content", encoding="utf-8")

    # Combined file (Text format)
    content = "--- file1.txt ---\nhello content\n--- end file1.txt ---\n"

    # Run verify
    sources = [("combined.txt", content)]
    results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[OK]" in out
    assert "content match" in out
    assert results['matches'] == 1

def test_verify_manifest_only(tmp_path, capsys):
    # Setup files
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("hello manifest", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello manifest").hexdigest()

    # Manifest without content
    manifest = [
        {"path": "file1.txt", "sha256": sha1}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Run verify
    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    results = verify_files(sources, root_folder=root)

    out, err = capsys.readouterr()
    assert "[OK]" in out
    assert "hash match" in out
    assert results['matches'] == 1
