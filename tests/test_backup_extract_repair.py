import sys
import os
import json
from pathlib import Path
import pytest
from unittest.mock import patch

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import extract_files, verify_files, restore_backups, main, _get_sha256_hash
import utils


def test_extract_creates_backups(tmp_path):
    """Test that extract_files creates .bak backups of existing files when create_backups is enabled."""
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    existing_file = output_dir / "foo.txt"
    existing_file.write_text("Old content")

    # Combined content with new data for foo.txt
    combined_content = json.dumps([
        {
            "path": "foo.txt",
            "content": "New content",
            "size_bytes": 11,
            "tokens": 2,
            "lines": 1,
            "language": "text",
            "sha256": "new_sha"
        }
    ])

    config = {
        "processing": {
            "create_backups": True
        }
    }

    stats = extract_files(
        sources=[("combined.json", combined_content)],
        output_folder=output_dir,
        config=config
    )

    assert stats["total_files"] == 1
    assert existing_file.read_text() == "New content"

    backup_file = output_dir / "foo.txt.bak"
    assert backup_file.exists()
    assert backup_file.read_text() == "Old content"


def test_repair_hash_mismatch_creates_backups(tmp_path):
    """Test that verify_files (repair=True) creates .bak backups for hash mismatches when create_backups is enabled."""
    existing_file = tmp_path / "bar.txt"
    existing_file.write_text("Old content")

    old_hash = _get_sha256_hash("Old content")
    new_hash = _get_sha256_hash("New content")

    combined_content = json.dumps([
        {
            "path": "bar.txt",
            "content": "New content",
            "size_bytes": 11,
            "tokens": 2,
            "lines": 1,
            "language": "text",
            "sha256": new_hash
        }
    ])

    config = {
        "processing": {
            "create_backups": True
        }
    }

    report = verify_files(
        sources=[("combined.json", combined_content)],
        root_folder=tmp_path,
        config=config,
        repair=True
    )

    assert report["repaired"] == 1
    assert existing_file.read_text() == "New content"

    backup_file = tmp_path / "bar.txt.bak"
    assert backup_file.exists()
    assert backup_file.read_text() == "Old content"


def test_repair_content_mismatch_creates_backups(tmp_path):
    """Test that verify_files (repair=True) creates .bak backups for content mismatches (no explicit hash) when create_backups is enabled."""
    existing_file = tmp_path / "baz.txt"
    existing_file.write_text("Old content")

    combined_content = json.dumps([
        {
            "path": "baz.txt",
            "content": "New content",
            "size_bytes": 11,
            "tokens": 2,
            "lines": 1,
            "language": "text"
        }
    ])

    config = {
        "processing": {
            "create_backups": True
        }
    }

    report = verify_files(
        sources=[("combined.json", combined_content)],
        root_folder=tmp_path,
        config=config,
        repair=True
    )

    assert report["repaired"] == 1
    assert existing_file.read_text() == "New content"

    backup_file = tmp_path / "baz.txt.bak"
    assert backup_file.exists()
    assert backup_file.read_text() == "Old content"


def test_extract_and_repair_restore_integration(tmp_path):
    """Verify CLI integration of extraction/repair backups and subsequent restore command."""
    extracted_dir = tmp_path / "ext"
    extracted_dir.mkdir()

    existing_file = extracted_dir / "qux.txt"
    existing_file.write_text("Original")

    combined_content = json.dumps([
        {
            "path": "qux.txt",
            "content": "Updated",
            "size_bytes": 7,
            "tokens": 1,
            "lines": 1,
            "language": "text"
        }
    ])

    combined_file = tmp_path / "combined.json"
    combined_file.write_text(combined_content)

    # CLI extraction with backups enabled
    with patch("sys.argv", ["sourcecombine.py", "--extract", str(combined_file), "-o", str(extracted_dir), "--create-backups"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    assert existing_file.read_text() == "Updated"
    backup_file = extracted_dir / "qux.txt.bak"
    assert backup_file.exists()
    assert backup_file.read_text() == "Original"

    # Now restore using the CLI
    with patch("sys.argv", ["sourcecombine.py", str(extracted_dir), "--restore"]):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    assert existing_file.read_text() == "Original"
    assert not backup_file.exists()
