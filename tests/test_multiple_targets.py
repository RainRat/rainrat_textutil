import os
import pytest
from pathlib import Path
from sourcecombine import main

def test_multiple_folders(tmp_path, monkeypatch, caplog):
    # Setup two folders
    folder1 = tmp_path / "folder1"
    folder1.mkdir()
    (folder1 / "file1.txt").write_text("content1")

    folder2 = tmp_path / "folder2"
    folder2.mkdir()
    (folder2 / "file2.txt").write_text("content2")

    output = tmp_path / "combined.txt"

    # Run main with both folders
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(folder1), str(folder2), "-o", str(output)])

    with caplog.at_level("INFO"):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert "Using 2 explicit target(s) with default settings." in caplog.text
    assert output.exists()
    content = output.read_text()
    assert "content1" in content
    assert "content2" in content

def test_single_file_target(tmp_path, monkeypatch, caplog):
    # Setup a single file
    file1 = tmp_path / "file1.txt"
    file1.write_text("content1")

    output = tmp_path / "combined.txt"

    # Run main with the file as target
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(file1), "-o", str(output)])

    with caplog.at_level("INFO"):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert "Using 1 explicit target(s) with default settings." in caplog.text
    assert output.exists()
    content = output.read_text()
    assert "content1" in content

def test_mixed_targets(tmp_path, monkeypatch, caplog):
    # Setup a folder and a file
    folder1 = tmp_path / "folder1"
    folder1.mkdir()
    (folder1 / "file1.txt").write_text("content1")

    file2 = tmp_path / "file2.txt"
    file2.write_text("content2")

    output = tmp_path / "combined.txt"

    # Run main with mixed targets
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(folder1), str(file2), "-o", str(output)])

    with caplog.at_level("INFO"):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert "Using 2 explicit target(s) with default settings." in caplog.text
    assert output.exists()
    content = output.read_text()
    assert "content1" in content
    assert "content2" in content

def test_config_with_extra_targets(tmp_path, monkeypatch, caplog):
    # Setup folders
    folder1 = tmp_path / "folder1"
    folder1.mkdir()
    (folder1 / "file1.txt").write_text("content1")

    folder2 = tmp_path / "folder2"
    folder2.mkdir()
    (folder2 / "file2.txt").write_text("content2")

    # Setup config that points to folder1 (which will be overridden)
    config_file = tmp_path / "config.yml"
    config_file.write_text(f"search:\n  root_folders:\n    - {str(folder1)}")

    output = tmp_path / "combined.txt"

    # Run main with config and folder2
    monkeypatch.setattr("sys.argv", ["sourcecombine.py", str(config_file), str(folder2), "-o", str(output)])

    with caplog.at_level("INFO"):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert f"Loading configuration from: {config_file}" in caplog.text
    assert "Overriding 'root_folders' with 1 explicit target(s)." in caplog.text
    assert output.exists()
    content = output.read_text()
    assert "content2" in content
    assert "content1" not in content # Overridden
