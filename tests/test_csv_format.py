import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import csv
import io
import pytest
from sourcecombine import find_and_combine_files, extract_files, verify_files

def test_csv_output(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").write_text("print('hello')", encoding="utf-8")
    (src_dir / "data.txt").write_text("some data", encoding="utf-8")

    output_file = tmp_path / "output.csv"
    config = {
        'search': {'root_folders': [str(src_dir)]},
        'output': {'file': str(output_file)},
        'pairing': {'enabled': False}
    }

    stats = find_and_combine_files(config, str(output_file), output_format='csv')
    assert stats['total_files'] == 2

    assert output_file.exists()
    with open(output_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        paths = {row['path'] for row in rows}
        assert paths == {"test.py", "data.txt"}

        # Verify columns
        expected_cols = ["path", "size_bytes", "tokens", "tokens_is_approx", "lines", "language", "sha256", "content", "modified"]
        assert all(col in reader.fieldnames for col in expected_cols)

def test_csv_extraction(tmp_path):
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    csv_content = (
        "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\n"
        "folder/file1.py,13,3,False,1,python,hash1,print('hi'),1700000000.0\n"
        "file2.txt,9,2,False,1,text,hash2,some text,1700000001.0\n"
    )
    csv_file = tmp_path / "combined.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    extract_files([(str(csv_file), csv_file.read_text())], str(output_dir))

    assert (output_dir / "folder/file1.py").read_text() == "print('hi')"
    assert (output_dir / "file2.txt").read_text() == "some text"

def test_csv_verify(tmp_path, capsys):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "match.txt").write_text("match", encoding="utf-8")
    (src_dir / "mismatch.txt").write_text("original", encoding="utf-8")

    # Generate CSV with metadata
    csv_content = (
        "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\n"
        "match.txt,5,1,False,1,text,,match,\n"
        "mismatch.txt,8,1,False,1,text,,wrong,\n"
        "missing.txt,7,1,False,1,text,,missing,\n"
    )
    csv_file = tmp_path / "combined.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    # Change mismatch.txt on disk to definitely mismatch if content verification is used
    (src_dir / "mismatch.txt").write_text("actual", encoding="utf-8")

    verify_files([(str(csv_file), csv_file.read_text())], str(src_dir))

    captured = capsys.readouterr().out
    assert "[OK]" in captured and "match.txt" in captured
    assert "[MISMATCH]" in captured and "mismatch.txt" in captured
    assert "[MISSING]" in captured and "missing.txt" in captured

def test_csv_extraction_fallback(tmp_path, monkeypatch):
    # Test that it finds combined_files.csv if no input is specified
    # Using CLI simulation to test the fallback in main() logic
    import sourcecombine
    import argparse
    from unittest.mock import patch

    monkeypatch.chdir(tmp_path)

    csv_content = (
        "path,size_bytes,tokens,tokens_is_approx,lines,language,sha256,content,modified\n"
        "fallback.txt,4,1,False,1,text,hash,data,1700000000.0\n"
    )
    (tmp_path / "combined_files.csv").write_text(csv_content, encoding="utf-8")

    output_dir = tmp_path / "out"
    output_dir.mkdir()

    test_args = [
        'sourcecombine.py',
        '--extract',
        '--output', str(output_dir)
    ]

    with patch('sys.argv', test_args):
        # Mock sys.exit to prevent test from exiting if something goes wrong
        with patch('sys.exit') as mock_exit:
            sourcecombine.main()
            # If fallback works, fallback.txt should exist
            assert (output_dir / "fallback.txt").read_text() == "data"
