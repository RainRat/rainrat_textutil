import subprocess

def test_cli_replace(tmp_path):
    # Create a dummy file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dummy_file = src_dir / "test.txt"
    dummy_file.write_text("Hello World\nKeep this line\nSensitive: secret_data\nEnd", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    # Run sourcecombine with --replace
    result = subprocess.run([
        "python3", "sourcecombine.py", str(src_dir),
        "-o", str(output_file),
        "--replace", "secret_data", "[REDACTED]",
        "--replace", "World", "Universe"
    ], capture_output=True, text=True)

    assert result.returncode == 0
    content = output_file.read_text(encoding="utf-8")

    assert "Hello Universe" in content
    assert "Sensitive: [REDACTED]" in content
    assert "Keep this line" in content

def test_cli_replace_line(tmp_path):
    # Create a dummy file with repetitive lines
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dummy_file = src_dir / "test.txt"
    dummy_file.write_text("Start\nDEBUG: log1\nDEBUG: log2\nDEBUG: log3\nMiddle\nDEBUG: log4\nEnd", encoding="utf-8")

    output_file = tmp_path / "combined.txt"

    # Run sourcecombine with --replace-line
    result = subprocess.run([
        "python3", "sourcecombine.py", str(src_dir),
        "-o", str(output_file),
        "--replace-line", "^DEBUG:.*$", "<LOGS>"
    ], capture_output=True, text=True)

    assert result.returncode == 0
    content = output_file.read_text(encoding="utf-8")

    # Blocks of DEBUG lines should be collapsed into a single <LOGS>
    assert "Start\n<LOGS>\nMiddle\n<LOGS>\nEnd" in content
    assert "DEBUG:" not in content
