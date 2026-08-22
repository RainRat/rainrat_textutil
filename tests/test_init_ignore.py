import pytest
import sys
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

import sourcecombine


def test_init_ignore_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_args = ["sourcecombine.py", "--init-ignore"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    ignore_file = tmp_path / ".sourcecombineignore"
    assert ignore_file.exists()
    content = ignore_file.read_text(encoding="utf-8")
    assert "# SourceCombine Ignore File (.sourcecombineignore)" in content
    assert "node_modules/" in content
    assert "*.log" in content


def test_init_ignore_custom_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom_target = tmp_path / "custom" / "my.ignore"
    test_args = ["sourcecombine.py", "--init-ignore", str(custom_target)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    assert custom_target.exists()
    content = custom_target.read_text(encoding="utf-8")
    assert "node_modules/" in content


def test_init_ignore_target_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target_dir = tmp_path / "subfolder"
    target_dir.mkdir()
    test_args = ["sourcecombine.py", "--init-ignore", str(target_dir)]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    expected_file = target_dir / ".sourcecombineignore"
    assert expected_file.exists()


def test_init_ignore_already_exists(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    ignore_file = tmp_path / ".sourcecombineignore"
    ignore_file.write_text("existing content", encoding="utf-8")

    test_args = ["sourcecombine.py", "--init-ignore"]
    monkeypatch.setattr(sys, "argv", test_args)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()

    assert exc_info.value.code == 1
    assert "already exists" in caplog.text


def test_init_ignore_mkdir_error(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    test_args = ["sourcecombine.py", "--init-ignore", "nested/ignore.txt"]
    monkeypatch.setattr(sys, "argv", test_args)

    with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                sourcecombine.main()

    assert exc_info.value.code == 1
    assert "Could not create target directory" in caplog.text


def test_init_ignore_write_error(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    test_args = ["sourcecombine.py", "--init-ignore", "test.ignore"]
    monkeypatch.setattr(sys, "argv", test_args)

    with patch("builtins.open", side_effect=OSError("Write failed")):
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                sourcecombine.main()

    assert exc_info.value.code == 1
    assert "Could not write the ignore file" in caplog.text


def test_init_ignore_with_files_from_error(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    list_file = tmp_path / "files.txt"
    list_file.write_text("a.py\n", encoding="utf-8")

    test_args = ["sourcecombine.py", "--init-ignore", "--files-from", str(list_file)]
    monkeypatch.setattr(sys, "argv", test_args)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc_info:
            sourcecombine.main()

    assert exc_info.value.code == 1
    assert "You cannot use --init-ignore and --files-from at the same time" in caplog.text


def test_init_ignore_stdout(monkeypatch, capsys):
    test_args = ["sourcecombine.py", "--init-ignore", "-"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr().out
    assert "# SourceCombine Ignore File (.sourcecombineignore)" in captured
    assert "node_modules/" in captured


def test_init_ignore_directory_trailing_slash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target_dir = tmp_path / "custom_dir"
    target_dir.mkdir()
    test_args = ["sourcecombine.py", "--init-ignore", f"{str(target_dir)}/"]
    monkeypatch.setattr(sys, "argv", test_args)

    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()

    assert exc_info.value.code == 0
    expected_file = target_dir / ".sourcecombineignore"
    assert expected_file.exists()

