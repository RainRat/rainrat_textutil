import json
import os
from pathlib import Path
import subprocess
import sys

def test_json_summary_file(tmp_path):
    """Verify that --json-summary writes a valid JSON file with expected keys."""
    # Create a dummy file to combine
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "hello.py").write_text("print('hello')")

    summary_path = tmp_path / "summary.json"
    output_path = tmp_path / "combined.txt"

    # Run sourcecombine
    cmd = [
        sys.executable, "sourcecombine.py",
        str(src_dir),
        "-o", str(output_path),
        "--json-summary", str(summary_path)
    ]
    subprocess.run(cmd, check=True)

    assert summary_path.exists()
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check for essential keys
    assert "total_files" in data
    assert data["total_files"] == 1
    assert "total_size_bytes" in data
    assert "duration_seconds" in data
    assert "destination" in data
    assert "source" in data

def test_json_summary_stderr(tmp_path):
    """Verify that --json-summary - writes to stderr."""
    # Create a dummy file to combine
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "hello.py").write_text("print('hello')")

    output_path = tmp_path / "combined.txt"

    # Run sourcecombine and capture stderr
    cmd = [
        sys.executable, "sourcecombine.py",
        str(src_dir),
        "-o", str(output_path),
        "--json-summary", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    assert "--- JSON Execution Summary ---" in result.stderr
    assert "total_files" in result.stderr
    # Verify it can be parsed
    json_start = result.stderr.find("{")
    json_end = result.stderr.rfind("}") + 1
    json_str = result.stderr[json_start:json_end]
    data = json.loads(json_str)
    assert data["total_files"] == 1

def test_json_summary_extract(tmp_path):
    """Verify that --json-summary works with --extract."""
    # Create a combined file
    combined_content = "--- file.txt ---\ncontent\n--- end file.txt ---"
    combined_file = tmp_path / "combined.txt"
    combined_file.write_text(combined_content)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    summary_path = tmp_path / "summary_extract.json"

    cmd = [
        sys.executable, "sourcecombine.py",
        "--extract", str(combined_file),
        "-o", str(extract_dir),
        "--json-summary", str(summary_path)
    ]
    subprocess.run(cmd, check=True)

    assert summary_path.exists()
    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_files"] == 1
    assert "duration_seconds" in data
