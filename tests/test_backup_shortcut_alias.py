import sys
from unittest.mock import patch
from pathlib import Path
import pytest
import sourcecombine


def test_cli_bak_alias(tmp_path, monkeypatch):
    """Test that passing --bak acts as a shortcut alias for --backup."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    test_args = ["sourcecombine.py", "--bak", "."]
    with patch.object(sys, "argv", test_args):
        with patch("sourcecombine.create_backups_for_targets") as mock_create_backups:
            mock_create_backups.return_value = (1, 0)
            with pytest.raises(SystemExit) as exc_info:
                sourcecombine.main()
            assert exc_info.value.code == 0
            assert mock_create_backups.called
