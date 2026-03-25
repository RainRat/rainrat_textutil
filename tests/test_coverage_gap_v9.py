import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import utils
import sourcecombine
from sourcecombine import _process_paired_files, extract_files, main
import pytest
import logging
from unittest.mock import MagicMock, patch

def test_process_paired_files_resolve_oserror(tmp_path, caplog):
    processor = MagicMock()
    # Mock Path.resolve to raise OSError
    with patch("sourcecombine.Path.resolve", side_effect=OSError("Simulated resolve error")):
        paired_items = [("test", [tmp_path / "test.py"])]
        with caplog.at_level(logging.INFO):
            _process_paired_files(
                paired_items,
                template="{{STEM}}.combined",
                source_exts=(".py",),
                header_exts=(),
                root_path=tmp_path,
                out_folder=tmp_path / "out",
                processor=processor,
                processing_bar=None,
                dry_run=True
            )
    # The OSError should be caught and passed (lines 1020-1021)
    # Since it's passed silently, we just verify it doesn't crash and proceeds to dry_run log
    assert "PAIR test" in caplog.text

def test_main_extract_directory(tmp_path, monkeypatch, capsys):
    combined_dir = tmp_path / "combined"
    combined_dir.mkdir()
    combined_file = combined_dir / "combined.json"
    combined_file.write_text('[{"path": "file1.txt", "content": "hello"}]')

    out_dir = tmp_path / "out"

    # Run main with --extract and the directory
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", "--extract", str(combined_dir), "--output", str(out_dir)])

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0

    assert (out_dir / "file1.txt").read_text() == "hello"

def test_main_extract_multiple_sources_summary(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "f1.json"
    f1.write_text('[{"path": "file1.txt", "content": "hello"}]')
    f2 = tmp_path / "f2.json"
    f2.write_text('[{"path": "file2.txt", "content": "world"}]')

    out_dir = tmp_path / "out"

    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", "--extract", str(f1), str(f2), "--output", str(out_dir)])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    # Line 3150: source_desc = f"from {len(sources)} sources"
    assert "from 2 sources" in captured.err

def test_extract_files_no_sources(caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as excinfo:
            extract_files([], "out_folder")

    assert excinfo.value.code == 1
    # Line 3338: logging.error("No extraction sources provided.")
    assert "No extraction sources provided." in caplog.text
