import os
import sys
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine


def test_target_directory_with_json_extension(tmp_path, monkeypatch):
    target_dir = tmp_path / "data.json"
    target_dir.mkdir()
    (target_dir / "sample.py").write_text("print('hello')", encoding="utf-8")

    out_file = tmp_path / "combined.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine.py", str(target_dir), "-o", str(out_file), "--quiet"],
    )

    sourcecombine.main()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "print('hello')" in content


def test_validate_config_empty_with_json_directory_target(tmp_path, monkeypatch):
    target_dir = tmp_path / "data.json"
    target_dir.mkdir()

    monkeypatch.setattr(
        sys,
        "argv",
        ["sourcecombine.py", "--validate-config", "", str(target_dir)],
    )

    try:
        sourcecombine.main()
    except SystemExit as exc:
        assert exc.code == 1


def test_ignore_file_duplicate_deduplication(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            "--list-ignores",
            "--ignore-file",
            ".gitignore,.gitignore",
        ],
    )

    try:
        sourcecombine.main()
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr().out
    assert "ACTIVE IGNORE PATTERNS" in captured


def test_repair_with_extract_mode(tmp_path, monkeypatch):
    archive_file = tmp_path / "archive.txt"
    archive_file.write_text('[{"path": "sample.py", "content": "print(\'hello\')"}]', encoding="utf-8")
    out_dir = tmp_path / "extracted"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sourcecombine.py",
            str(archive_file),
            "--repair",
            "--extract",
            "-o",
            str(out_dir),
            "--dry-run",
        ],
    )

    try:
        sourcecombine.main()
    except SystemExit as exc:
        assert exc.code == 0
