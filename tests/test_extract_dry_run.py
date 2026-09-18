import json
from pathlib import Path
from sourcecombine import extract_files, main


def test_extract_files_dry_run_library(tmp_path, caplog):
    """Test that extract_files in dry_run mode does not create any files on disk."""
    combined_content = (
        "--- hello.py ---\n"
        "print('hello world')\n"
        "--- end hello.py ---\n"
        "--- nested/sub.txt ---\n"
        "some text\n"
        "--- end nested/sub.txt ---\n"
    )
    output_dir = tmp_path / "extracted_out"

    with caplog.at_level("INFO"):
        stats = extract_files(
            sources=[("test_source", combined_content)],
            output_folder=output_dir,
            dry_run=True,
            json_format=False,
        )

    # Output folder and extracted files should not be created on disk
    assert not (output_dir / "hello.py").exists()
    assert not (output_dir / "nested" / "sub.txt").exists()
    assert "Extraction dry run complete. 2 file(s) would be created" in caplog.text
    assert stats["total_files"] == 2


def test_extract_files_dry_run_json(tmp_path):
    """Test extract_files in dry_run mode with json_format=True."""
    combined_content = (
        "--- hello.py ---\n"
        "print('hello world')\n"
        "--- end hello.py ---\n"
    )
    output_dir = tmp_path / "extracted_json_out"

    stats = extract_files(
        sources=[("test_source", combined_content)],
        output_folder=output_dir,
        dry_run=True,
        json_format=True,
    )

    assert stats["total_files"] == 1
    assert not (output_dir / "hello.py").exists()


def test_cli_extract_dry_run(tmp_path, monkeypatch):
    """Test CLI execution of --extract with --dry-run."""
    combined_file = tmp_path / "combined_files.txt"
    combined_file.write_text(
        "--- sample.py ---\n"
        "a = 1\n"
        "--- end sample.py ---\n",
        encoding="utf-8",
    )
    extract_target = tmp_path / "target_dir"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--extract",
            str(combined_file),
            "--output",
            str(extract_target),
            "--dry-run",
        ],
    )

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    assert not (extract_target / "sample.py").exists()


def test_cli_extract_dry_run_json(tmp_path, monkeypatch, capsys):
    """Test CLI execution of --extract with --dry-run and --json."""
    combined_file = tmp_path / "combined_files.txt"
    combined_file.write_text(
        "--- sample.py ---\n"
        "a = 1\n"
        "--- end sample.py ---\n",
        encoding="utf-8",
    )
    extract_target = tmp_path / "target_dir"

    monkeypatch.setattr(
        "sys.argv",
        [
            "sourcecombine.py",
            "--extract",
            str(combined_file),
            "--output",
            str(extract_target),
            "--dry-run",
            "--json",
        ],
    )

    try:
        main()
    except SystemExit as e:
        assert e.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["dry_run"] is True
    assert data["files"][0]["status"] == "WOULD_EXTRACT"
    assert not (extract_target / "sample.py").exists()
