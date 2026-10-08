import json
import sys
import pytest
import sourcecombine


def test_cli_extract_alias_extr(tmp_path, monkeypatch):
    """Verify that --extr invokes file extraction correctly."""
    combined_file = tmp_path / "combined.json"
    data = [
        {
            "path": "hello.py",
            "content": "print('hello world')\n",
            "size_bytes": 21,
            "tokens": 5,
            "lines": 1,
            "language": "python",
            "sha256": "abc"
        }
    ]
    combined_file.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "out_extr"

    monkeypatch.setattr(
        sys, "argv",
        ["sourcecombine.py", "--extr", str(combined_file), "-o", str(out_dir)]
    )
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0

    extracted_file = out_dir / "hello.py"
    assert extracted_file.is_file()
    assert extracted_file.read_text(encoding="utf-8") == "print('hello world')\n"


def test_cli_extract_alias_xtr(tmp_path, monkeypatch):
    """Verify that --xtr invokes file extraction correctly."""
    combined_file = tmp_path / "combined.json"
    data = [
        {
            "path": "app.py",
            "content": "import sys\n",
            "size_bytes": 11,
            "tokens": 3,
            "lines": 1,
            "language": "python",
            "sha256": "def"
        }
    ]
    combined_file.write_text(json.dumps(data), encoding="utf-8")
    out_dir = tmp_path / "out_xtr"

    monkeypatch.setattr(
        sys, "argv",
        ["sourcecombine.py", "--xtr", str(combined_file), "-o", str(out_dir)]
    )
    with pytest.raises(SystemExit) as exc_info:
        sourcecombine.main()
    assert exc_info.value.code == 0

    extracted_file = out_dir / "app.py"
    assert extracted_file.is_file()
    assert extracted_file.read_text(encoding="utf-8") == "import sys\n"
