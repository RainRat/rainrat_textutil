import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from sourcecombine import main

def test_verify_json_output(tmp_path, capsys):
    """Test that --verify --json produces valid JSON output with correct results."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # 1. Create some dummy files
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding='utf-8')

        file2 = tmp_path / "file2.txt"
        file2.write_text("content2", encoding='utf-8')

        # 2. Create a combined JSON file for verification
        combined_data = [
            {"path": "file1.txt", "content": "content1"},
            {"path": "file2.txt", "content": "wrong content"},
            {"path": "missing.txt", "content": "missing"}
        ]
        combined_file = tmp_path / "combined.json"
        combined_file.write_text(json.dumps(combined_data), encoding='utf-8')

        # 3. Run the tool with --verify and --json
        test_args = ["sourcecombine.py", "--verify", str(combined_file), "--json"]
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 0

        # 4. Capture and parse output
        captured = capsys.readouterr()
        results = json.loads(captured.out)

        # 5. Verify results
        assert results["matches"] == 1
        assert results["mismatches"] == 1
        assert results["missing"] == 1
        assert results["total"] == 3
        assert results["repaired"] == 0
    finally:
        os.chdir(old_cwd)

def test_verify_json_no_output_on_stdout(tmp_path, capsys):
    """Test that standard report is suppressed when --json is used."""
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        file1 = tmp_path / "file1.txt"
        file1.write_text("content1", encoding='utf-8')

        combined_data = [{"path": "file1.txt", "content": "content1"}]
        combined_file = tmp_path / "combined.json"
        combined_file.write_text(json.dumps(combined_data), encoding='utf-8')

        test_args = ["sourcecombine.py", "--verify", str(combined_file), "--json"]
        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        # Standard report contains "=== Verification Report ==="
        assert "Verification Report" not in captured.out
        # But it should be valid JSON
        results = json.loads(captured.out)
        assert results["matches"] == 1
    finally:
        os.chdir(old_cwd)
