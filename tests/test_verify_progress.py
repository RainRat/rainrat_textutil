import sys
import json
import hashlib
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from sourcecombine import verify_files, _progress_enabled

def test_verify_files_progress_bar_creation_and_postfix_updates(tmp_path, capsys, monkeypatch, mocker):
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

    monkeypatch.setenv("CI", "")
    monkeypatch.setattr("sourcecombine._progress_enabled", lambda dry_run: True)

    mock_bar = MagicMock()
    mock_bar.__iter__.side_effect = lambda: iter([("file1.txt", "hello world", {"sha256": sha1})])

    mock_progress_bar_func = mocker.patch("sourcecombine._progress_bar", return_value=mock_bar)

    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    verify_files(sources, root_folder=root, dry_run=False)

    mock_progress_bar_func.assert_called_once()
    mock_bar.set_postfix.assert_called_with(ok=1, mismatch=0, missing=0, repaired=0)
    mock_bar.close.assert_called_once()

def test_verify_files_progress_bar_write_routing(tmp_path, monkeypatch, mocker):
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

    monkeypatch.setenv("CI", "")
    monkeypatch.setattr("sourcecombine._progress_enabled", lambda dry_run: True)

    mock_bar = MagicMock()
    mock_bar.__iter__.side_effect = lambda: iter([("file1.txt", "hello world", {"sha256": sha1})])

    mocker.patch("sourcecombine._progress_bar", return_value=mock_bar)

    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    verify_files(sources, root_folder=root, dry_run=False)

    mock_bar.write.assert_called()
