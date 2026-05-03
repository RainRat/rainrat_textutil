import sys
import os
import csv
import io
from pathlib import Path

import pytest

from sourcecombine import find_and_combine_files, extract_files, main

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

def test_csv_output(tmp_path):
    # Setup
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.py").write_text("print('a')", encoding="utf-8")

    output_file = tmp_path / "output.csv"

    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {'file': str(output_file)},
    }

    # Execute
    find_and_combine_files(config, str(output_file), output_format='csv')

    # Verify
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")

    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)

    assert len(rows) == 1
    row = rows[0]

    expected_fields = ["path", "size_bytes", "tokens", "tokens_is_approx", "lines", "language", "sha256", "content", "modified"]
    assert all(field in row for field in expected_fields)
    assert row["path"] == "a.py"
    assert row["content"] == "print('a')"
    assert row["language"] == "python"

def test_csv_extraction(tmp_path):
    output_dir = tmp_path / "extracted"

    # Header: path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified
    content = (
        "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\n"
        "main.py,10,2,False,1,python,hash1,print('hello'),1234567890.0\n"
    )

    extract_files(content, str(output_dir), source_name="test.csv")

    assert (output_dir / "main.py").read_text(encoding="utf-8") == "print('hello')"

def test_csv_extraction_malformed(tmp_path, caplog):
    output_dir = tmp_path / "extracted"

    # Malformed 'modified' column (not a float) should trigger ValueError in _parse_combined_content
    # Line 4445: 'modified': float(row['modified']) if row.get('modified') else None,
    content = (
        "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\n"
        "main.py,10,2,False,1,python,hash1,print('hello'),invalid_date\n"
    )

    # Should not raise exception but also not extract anything due to the try-except block
    # It will exit(1) because no files were found to extract
    with pytest.raises(SystemExit) as exc:
        extract_files(content, str(output_dir), source_name="test.csv")
    assert exc.value.code == 1

    assert not (output_dir / "main.py").exists()

def test_csv_cli_shortcuts(tmp_path, monkeypatch):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello")

    # 1. Test --csv flag
    output_csv = tmp_path / "out1.csv"
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', str(src_dir), '--csv', '-o', str(output_csv)])
    main()
    assert output_csv.exists()
    assert output_csv.read_text().startswith("path,size_bytes,tokens,")

    # 2. Test .csv extension auto-detection
    output_auto = tmp_path / "out2.csv"
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', str(src_dir), '-o', str(output_auto)])
    main()
    assert output_auto.exists()
    assert output_auto.read_text().startswith("path,size_bytes,tokens,")

def test_csv_cli_default_filename_with_format(tmp_path, monkeypatch):
    """Cover sourcecombine.py line 4187: auto-setting default filename to combined_files.csv."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("hello")

    monkeypatch.chdir(tmp_path)
    # We use --csv but NO --output. It should create combined_files.csv.
    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', str(src_dir), '--csv'])

    main()
    assert (tmp_path / "combined_files.csv").exists()
