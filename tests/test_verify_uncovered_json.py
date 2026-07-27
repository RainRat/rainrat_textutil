import json
import hashlib
import sys
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from sourcecombine import verify_files, _generate_project_overview, main
import utils

@pytest.fixture(autouse=True)
def ensure_pyperclip_spec():
    import pyperclip
    if not hasattr(pyperclip, '__spec__'):
        pyperclip.__spec__ = MagicMock(name='pyperclip_spec')
    yield

def test_verify_strip_components_too_many(caplog):
    caplog.set_level(logging.WARNING)
    sources = [("manifest.json", '[{"path": "file.txt"}]')]
    results = verify_files(sources, root_folder=Path("."), strip_components=2, json_format=True)
    assert results['matches'] == 0
    assert any("Skipping path with fewer than 2 components: file.txt" in record.message for record in caplog.records)

def test_verify_oserror_during_file_creation_in_repair(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    manifest = [{"path": "file1.txt", "content": "hello world"}]
    sources = [("manifest.json", json.dumps(manifest))]
    with patch.object(Path, "write_text", side_effect=OSError("Permission denied")):
        results = verify_files(sources, root_folder=root, repair=True, dry_run=False, json_format=True)
        assert results['missing'] == 1

def test_verify_hash_mismatch_dry_run(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    sha1 = hashlib.sha256(b"expected content").hexdigest()
    manifest = [{"path": "file1.txt", "sha256": sha1, "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    results = verify_files(sources, root_folder=root, repair=True, dry_run=True, json_format=True)
    assert results['repaired'] == 1

def test_verify_hash_mismatch_repaired_successfully(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    sha1 = hashlib.sha256(b"expected content").hexdigest()
    manifest = [{"path": "file1.txt", "sha256": sha1, "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    results = verify_files(sources, root_folder=root, repair=True, dry_run=False, json_format=True)
    assert results['repaired'] == 1
    assert file1.read_text(encoding="utf-8") == "expected content"

def test_verify_hash_mismatch_repair_oserror(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    sha1 = hashlib.sha256(b"expected content").hexdigest()
    manifest = [{"path": "file1.txt", "sha256": sha1, "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    with patch.object(Path, "write_text", side_effect=OSError("Write failure")):
        results = verify_files(sources, root_folder=root, repair=True, dry_run=False, json_format=True)
        assert results['mismatches'] == 1

def test_verify_sha256_read_bytes_oserror(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    sha1 = hashlib.sha256(b"expected content").hexdigest()
    manifest = [{"path": "file1.txt", "sha256": sha1, "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    with patch.object(Path, "read_bytes", side_effect=OSError("Read failure")):
        results = verify_files(sources, root_folder=root, repair=False, dry_run=False, json_format=True)
        assert results['mismatches'] == 1

def test_verify_content_mismatch_dry_run(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    manifest = [{"path": "file1.txt", "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    results = verify_files(sources, root_folder=root, repair=True, dry_run=True, json_format=True)
    assert results['repaired'] == 1

def test_verify_content_mismatch_repaired_successfully(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    manifest = [{"path": "file1.txt", "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    results = verify_files(sources, root_folder=root, repair=True, dry_run=False, json_format=True)
    assert results['repaired'] == 1
    assert file1.read_text(encoding="utf-8") == "expected content"

def test_verify_content_mismatch_repair_oserror(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    manifest = [{"path": "file1.txt", "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    with patch.object(Path, "write_text", side_effect=OSError("Write failure")):
        results = verify_files(sources, root_folder=root, repair=True, dry_run=False, json_format=True)
        assert results['mismatches'] == 1

def test_verify_content_mismatch_no_repair(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    manifest = [{"path": "file1.txt", "content": "expected content"}]
    sources = [("manifest.json", json.dumps(manifest))]
    results = verify_files(sources, root_folder=root, repair=False, dry_run=False, json_format=True)
    assert results['mismatches'] == 1

def test_verify_skipped_no_hash_or_content(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    file1 = root / "file1.txt"
    file1.write_text("different content", encoding="utf-8")
    manifest = [{"path": "file1.txt"}]
    sources = [("manifest.json", json.dumps(manifest))]
    results = verify_files(sources, root_folder=root, repair=False, dry_run=False, json_format=True)
    assert results['matches'] == 0
    assert results['mismatches'] == 0

def test_project_overview_comment_removal():
    stats = {"total_files": 1}
    processing_opts = {"remove_comments": True}
    overview = _generate_project_overview(stats, processing_opts=processing_opts)
    assert "Comment removal" in overview

def test_cli_config_null_initialization(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "search": {
            "root_folders": [str(tmp_path)],
            "ignore_files": None,
            "exclude_extensions": None
        }
    }), encoding="utf-8")
    args = ["sourcecombine.py", "--config", str(config_path), "--ignore-file", "test_ignore.txt", "--exclude-extension", ".bin", "--dry-run"]
    with patch.object(sys, "argv", args):
        try:
            main()
        except SystemExit as exc:
            assert exc.code == 0

def test_cli_mirror_mode_missing_output(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "search": {
            "root_folders": [str(tmp_path)],
        },
        "output": {
            "mirror": True,
            "folder": "",
            "file": ""
        }
    }), encoding="utf-8")
    args = ["sourcecombine.py", "--config", str(config_path)]
    with patch.object(sys, "argv", args):
        with pytest.raises(utils.InvalidConfigError) as exc:
            main()
        assert "You must set an output folder for mirror mode." in str(exc.value)
