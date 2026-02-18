import os
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add the project root to sys.path so we can import sourcecombine
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import FileProcessor, InvalidConfigError
import sourcecombine

def test_backup_failure_raises_invalid_config_error(tmp_path):
    """
    Verify that if creating a backup fails (e.g., due to permission error),
    FileProcessor raises InvalidConfigError to prevent data loss.
    """
    file_path = tmp_path / "important_code.py"
    original_content = "print('hello')"
    file_path.write_text(original_content, encoding="utf-8")

    config = {
        "processing": {
            "apply_in_place": True,
            "create_backups": True,
            # Ensure content changes so backup is attempted
            "regex_replacements": [
                {"pattern": "hello", "replacement": "world"}
            ]
        },
        "output": {}
    }

    processor = FileProcessor(config, {}, dry_run=False)

    # Mock shutil.copy2 to raise OSError
    # We patch sourcecombine.shutil.copy2 because sourcecombine imports shutil
    with patch("sourcecombine.shutil.copy2", side_effect=OSError("Disk full")):
        with pytest.raises(InvalidConfigError) as excinfo:
            # Pass a dummy outfile because process_and_write writes to it if successful
            # But here it should fail before writing to outfile
            processor.process_and_write(file_path, tmp_path, MagicMock())[:-1]

    assert "Failed to create backup" in str(excinfo.value)
    assert "Disk full" in str(excinfo.value)

    # Verify original file is untouched (process_and_write should fail before overwriting)
    assert file_path.read_text(encoding="utf-8") == original_content
