import json
import hashlib
from pathlib import Path
import pytest
from sourcecombine import verify_files, main
import sys

def test_verify_files_filtering(tmp_path, capsys):
    # Setup files on disk
    root = tmp_path / "project"
    root.mkdir()

    file1 = root / "file1.txt"
    file1.write_text("hello txt", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello txt").hexdigest()

    file2 = root / "file2.py"
    file2.write_text("hello py", encoding="utf-8")
    sha2 = hashlib.sha256(b"hello py").hexdigest()

    # Create a manifest listing both files.
    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello txt"},
        {"path": "file2.py", "sha256": sha2, "content": "hello py"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Config that only allows .py extensions
    config = {
        "search": {
            "effective_allowed_extensions": (".py",),
            "effective_exclude_extensions": ()
        },
        "filters": {}
    }

    # Run verify
    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    results = verify_files(sources, root_folder=root, config=config)

    out, err = capsys.readouterr()

    # file1.txt should have been filtered out and therefore NOT verified.
    # file2.py should have been verified successfully.
    assert "[OK]" in out
    assert "file2.py" in out
    assert "file1.txt" not in out
    assert results['matches'] == 1
    assert results['total'] == 1


def test_verify_files_filtering_by_language(tmp_path, capsys):
    # Setup files on disk
    root = tmp_path / "project"
    root.mkdir()

    file1 = root / "file1.txt"
    file1.write_text("hello txt", encoding="utf-8")
    sha1 = hashlib.sha256(b"hello txt").hexdigest()

    file2 = root / "file2.py"
    file2.write_text("hello py", encoding="utf-8")
    sha2 = hashlib.sha256(b"hello py").hexdigest()

    # Create a manifest listing both files.
    manifest = [
        {"path": "file1.txt", "sha256": sha1, "content": "hello txt"},
        {"path": "file2.py", "sha256": sha2, "content": "hello py"}
    ]
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Config that excludes python
    config = {
        "search": {
            "effective_allowed_extensions": (),
            "effective_exclude_extensions": (),
            "exclude_languages": ["python"]
        },
        "filters": {}
    }

    # Run verify
    sources = [("manifest.json", manifest_file.read_text(encoding="utf-8"))]
    results = verify_files(sources, root_folder=root, config=config)

    out, err = capsys.readouterr()

    # file2.py (python) should have been excluded.
    # file1.txt (text) should be verified.
    assert "[OK]" in out
    assert "file1.txt" in out
    assert "file2.py" not in out
    assert results['matches'] == 1
    assert results['total'] == 1


def test_verify_cli_output_folder(tmp_path, capsys, monkeypatch):
    # Setup a manifest file to verify
    manifest = [
        {"path": "foo.txt", "sha256": hashlib.sha256(b"verified foo").hexdigest(), "content": "verified foo"}
    ]
    manifest_file = tmp_path / "combined_files.json"
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")

    # Target folder (args.output) where foo.txt resides
    target_dir = tmp_path / "different_target"
    target_dir.mkdir()
    foo_file = target_dir / "foo.txt"
    foo_file.write_text("verified foo", encoding="utf-8")

    # Patch sys.argv and call main()
    monkeypatch.setattr(sys, "argv", [
        "sourcecombine.py",
        "--verify",
        str(manifest_file),
        "--output",
        str(target_dir)
    ])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0

    out, err = capsys.readouterr()
    assert "[OK]" in out
    assert "foo.txt" in out
    assert "hash match" in out
