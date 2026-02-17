import os
import subprocess
import pytest
from pathlib import Path

def test_line_numbers_cli(tmp_path):
    # Create some dummy files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Hello\nWorld", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    # Run sourcecombine with --line-numbers
    result = subprocess.run(
        ["python3", "sourcecombine.py", str(src_dir), "-o", str(output_file), "--line-numbers"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    content = output_file.read_text(encoding="utf-8")

    # Check if line numbers are present
    assert "1: Hello" in content
    assert "2: World" in content

def test_line_numbers_short_flag_cli(tmp_path):
    # Create some dummy files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("Line One\nLine Two", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    # Run sourcecombine with -n
    result = subprocess.run(
        ["python3", "sourcecombine.py", str(src_dir), "-o", str(output_file), "-n"],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    content = output_file.read_text(encoding="utf-8")

    # Check if line numbers are present
    assert "1: Line One" in content
    assert "2: Line Two" in content
