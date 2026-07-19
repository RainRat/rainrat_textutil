import json
import hashlib
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import verify_files, main

@pytest.fixture(autouse=True)
def ensure_pyperclip_spec():
    import pyperclip
    if not hasattr(pyperclip, '__spec__'):
        pyperclip.__spec__ = MagicMock(name='pyperclip_spec')
    yield

def test_verify_files_returns_json_format(tmp_path, capsys):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("hello world", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello world").hexdigest()

    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello world"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]

    results = verify_files(sources, root_folder=root, json_format=True)
    captured = capsys.readouterr()
    printed = captured.out

    assert results['matches'] == 1
    data = json.loads(printed)
    assert data["title"] == "Verification Report"
    assert len(data["files"]) == 1
    assert data["files"][0]["path"] == "file1.txt"
    assert data["files"][0]["status"] == "OK"
    assert data["files"][0]["detail"] == "hash match"
    assert data["summary"]["matches"] == 1
    assert data["summary"]["total"] == 1

def test_verify_files_json_mismatch_and_missing(tmp_path, capsys):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("wrong content", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello world").hexdigest()

    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello world"},
        {"path": "missing.txt", "sha256": "some_sha", "content": "hello missed"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]

    results = verify_files(sources, root_folder=root, json_format=True)
    captured = capsys.readouterr()
    printed = captured.out

    assert results['matches'] == 0
    assert results['mismatches'] == 1
    assert results['missing'] == 1

    data = json.loads(printed)
    assert len(data["files"]) == 2

    file1_res = next(f for f in data["files"] if f["path"] == "file1.txt")
    assert file1_res["status"] == "MISMATCH"
    assert file1_res["detail"] == "hash mismatch"

    missing_res = next(f for f in data["files"] if f["path"] == "missing.txt")
    assert missing_res["status"] == "MISSING"
    assert missing_res["detail"] == "missing file"

def test_verify_files_json_repair_dry_run(tmp_path, capsys):
    root = tmp_path / "project"
    root.mkdir()
    sha1 = hashlib.sha256(b"hello world").hexdigest()

    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello world"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]

    results = verify_files(sources, root_folder=root, repair=True, dry_run=True, json_format=True)
    captured = capsys.readouterr()
    printed = captured.out

    assert results['repaired'] == 1
    assert not (root / "file1.txt").exists()

    data = json.loads(printed)
    assert data["files"][0]["status"] == "REPAIR"
    assert data["files"][0]["detail"] == "would create missing file"

def test_verify_files_json_repair_real(tmp_path, capsys):
    root = tmp_path / "project"
    root.mkdir()
    sha1 = hashlib.sha256(b"hello world").hexdigest()

    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello world"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]

    results = verify_files(sources, root_folder=root, repair=True, dry_run=False, json_format=True)
    captured = capsys.readouterr()
    printed = captured.out

    assert results['repaired'] == 1
    assert (root / "file1.txt").exists()
    assert (root / "file1.txt").read_text(encoding="utf-8") == "hello world"

    data = json.loads(printed)
    assert data["files"][0]["status"] == "REPAIRED"
    assert data["files"][0]["detail"] == "created missing file"

def test_verify_cli_integration_with_json_flag(tmp_path, capsys):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("hello content", encoding="utf-8")

    content = "--- file1.txt ---\nhello content\n--- end file1.txt ---\n"
    combined_file = tmp_path / "combined_files.txt"
    combined_file.write_text(content, encoding="utf-8")

    with patch.object(sys, 'argv', ["sourcecombine.py", "--verify", str(combined_file), "--json"]):
        with patch("os.getcwd", return_value=str(root)):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["title"] == "Verification Report"
    assert len(data["files"]) == 1
    assert data["files"][0]["path"] == "file1.txt"
    assert data["files"][0]["status"] == "OK"
    assert data["files"][0]["detail"] == "content match"
