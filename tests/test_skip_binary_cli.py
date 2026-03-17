from sourcecombine import main
import sys
from unittest.mock import patch

def test_skip_binary_flag(tmp_path, caplog):
    """Verify that the --skip-binary flag correctly filters binary files."""
    # Create a text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is a text file.", encoding="utf-8")

    # Create a binary file
    binary_file = tmp_path / "test.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

    output_file = tmp_path / "combined.txt"

    # Run sourcecombine with --skip-binary
    test_args = [
        "sourcecombine.py",
        str(tmp_path),
        "-o", str(output_file),
        "--skip-binary"
    ]

    with patch.object(sys, 'argv', test_args):
        main()

    # Verify output
    content = output_file.read_text(encoding="utf-8")
    assert "test.txt" in content
    assert "test.bin" not in content

def test_ai_preset_enables_skip_binary(tmp_path):
    """Verify that the --ai preset automatically enables binary filtering."""
    # Create a text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is a text file.", encoding="utf-8")

    # Create a binary file
    binary_file = tmp_path / "test.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

    output_file = tmp_path / "combined.md"

    # Run sourcecombine with --ai
    test_args = [
        "sourcecombine.py",
        str(tmp_path),
        "-o", str(output_file),
        "--ai"
    ]

    with patch.object(sys, 'argv', test_args):
        main()

    # Verify output
    content = output_file.read_text(encoding="utf-8")
    assert "test.txt" in content
    assert "test.bin" not in content

    # Also verify some other AI preset features are active
    assert "Table of Contents" in content
    assert "Project Structure" in content
    assert "```" in content

def test_no_skip_binary_by_default(tmp_path):
    """Verify that binary files are included by default (unless configured otherwise)."""
    # Create a text file
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is a text file.", encoding="utf-8")

    # Create a binary file
    binary_file = tmp_path / "test.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

    output_file = tmp_path / "combined.txt"

    # Run sourcecombine without --skip-binary
    test_args = [
        "sourcecombine.py",
        str(tmp_path),
        "-o", str(output_file)
    ]

    with patch.object(sys, 'argv', test_args):
        main()

    # Verify output - by default binary files ARE included (but might be mangled/empty if read as text)
    # Actually _looks_binary just flags it. read_file_best_effort will try to read it.
    content = output_file.read_text(encoding="utf-8", errors="replace")
    assert "test.bin" in content
