import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import json
import sys
from pathlib import Path
from unittest.mock import patch
import sourcecombine
from sourcecombine import main, find_and_combine_files


def test_list_excluded_plain_text(capsys, tmp_path):
    (tmp_path / "included.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "excluded.txt").write_text("text content", encoding="utf-8")

    with patch.object(
        sys,
        "argv",
        ["sourcecombine.py", str(tmp_path), "-x", "*.txt", "--list-excluded"],
    ):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    assert "excluded.txt (excluded)" in captured.out
    assert "included.py" not in captured.out
    assert "EXCLUDED LISTING" in captured.err


def test_list_excluded_json(capsys, tmp_path):
    (tmp_path / "included.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "excluded.txt").write_text("text content", encoding="utf-8")

    with patch.object(
        sys,
        "argv",
        ["sourcecombine.py", str(tmp_path), "-x", "*.txt", "--list-exc", "--json"],
    ):
        try:
            main()
        except SystemExit:
            pass

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["path"] == "excluded.txt"
    assert data[0]["reason"] == "excluded"
    assert "EXCLUDED LISTING" not in captured.err
    assert "EXCLUDED LISTING" not in captured.out
    assert "Operation: Combine" not in captured.err


def test_list_excluded_extension_and_size_filters(capsys, tmp_path):
    (tmp_path / "app.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "data.csv").write_text("a,b,c", encoding="utf-8")
    (tmp_path / "large.py").write_text("x" * 500, encoding="utf-8")

    config = {
        "search": {
            "root_folders": [str(tmp_path)],
            "effective_allowed_extensions": (".py",),
        },
        "filters": {
            "max_size_bytes": 100,
        },
    }

    stats = find_and_combine_files(
        config,
        output_path=None,
        list_excluded=True,
        json_format=True,
    )

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    reasons = {item["path"]: item["reason"] for item in data}

    assert reasons.get("data.csv") == "extension"
    assert reasons.get("large.py") == "too_large"
    assert "app.py" not in reasons
