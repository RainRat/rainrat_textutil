import pytest
from unittest.mock import patch
import sourcecombine


def test_preset_ai_by_name(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--preset", "ai", "--dry-run"]):
        sourcecombine.main()


def test_preset_analyze_by_name(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--preset", "ANALYZE"]):
        sourcecombine.main()


def test_preset_review_by_name(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--preset", "review", "--dry-run"]):
        sourcecombine.main()


def test_review_flag_directly(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--review", "--dry-run"]):
        sourcecombine.main()


def test_invalid_preset_name(caplog, tmp_path):
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--preset", "invalid_name"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 1
    assert "Unknown preset 'invalid_name'" in caplog.text


def test_preset_short_flag_aliases(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("print('hello')")
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--preset=-A"]):
        sourcecombine.main()
    with patch("sys.argv", ["sourcecombine", str(tmp_path), "--preset=-a", "--dry-run"]):
        sourcecombine.main()


