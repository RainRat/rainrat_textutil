import os
import json
from pathlib import Path
from sourcecombine import verify_files

def test_verify_repair_missing(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    # Combined content with one missing file
    combined_data = [
        {
            "path": "missing.txt",
            "content": "new content",
            "size_bytes": 11
        }
    ]
    combined_json = json.dumps(combined_data)

    sources = [("test.json", combined_json)]

    # Run repair
    results = verify_files(sources, root_folder=root, repair=True)

    assert results['repaired'] == 1
    assert results['missing'] == 0
    assert (root / "missing.txt").exists()
    assert (root / "missing.txt").read_text() == "new content"

def test_verify_repair_mismatch(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    existing_file = root / "mismatch.txt"
    existing_file.write_text("old content")

    # Combined content with mismatched content
    combined_data = [
        {
            "path": "mismatch.txt",
            "content": "repaired content",
            "size_bytes": 16
        }
    ]
    combined_json = json.dumps(combined_data)

    sources = [("test.json", combined_json)]

    # Run repair
    results = verify_files(sources, root_folder=root, repair=True)

    assert results['repaired'] == 1
    assert results['mismatches'] == 0
    assert existing_file.read_text() == "repaired content"

def test_verify_repair_dry_run(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    # Missing file
    combined_data = [
        {
            "path": "missing.txt",
            "content": "should not exist",
            "size_bytes": 16
        }
    ]
    combined_json = json.dumps(combined_data)

    sources = [("test.json", combined_json)]

    # Run repair with dry run
    results = verify_files(sources, root_folder=root, repair=True, dry_run=True)

    assert results['repaired'] == 1
    assert not (root / "missing.txt").exists()

def test_verify_repair_no_content(tmp_path):
    root = tmp_path / "root"
    root.mkdir()

    # Manifest-only (no content)
    combined_data = [
        {
            "path": "missing.txt",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # empty file hash
            "size_bytes": 0
        }
    ]
    combined_json = json.dumps(combined_data)

    sources = [("test.json", combined_json)]

    # Run repair - should not be able to repair without content
    results = verify_files(sources, root_folder=root, repair=True)

    assert results['repaired'] == 0
    assert results['missing'] == 1
    assert not (root / "missing.txt").exists()
