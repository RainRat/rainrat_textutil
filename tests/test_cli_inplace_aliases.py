import sys
from unittest.mock import patch
import sourcecombine


def test_cli_alias_in_place(tmp_path, monkeypatch):
    """Verify that --in-place acts as a shortcut alias for --apply-in-place."""
    test_file = tmp_path / "code.py"
    test_file.write_text("# comment\nprint('hello')\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    test_args = ["sourcecombine.py", "--in-place", "-R", "."]
    with patch.object(sys, "argv", test_args):
        sourcecombine.main()

    # Comment should be removed in place
    updated_content = test_file.read_text(encoding="utf-8")
    assert "# comment" not in updated_content
    assert "print('hello')" in updated_content


def test_cli_alias_inplace(tmp_path, monkeypatch):
    """Verify that --inplace acts as a shortcut alias for --apply-in-place."""
    test_file = tmp_path / "code.py"
    test_file.write_text("# comment\nprint('world')\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    test_args = ["sourcecombine.py", "--inplace", "-R", "."]
    with patch.object(sys, "argv", test_args):
        sourcecombine.main()

    # Comment should be removed in place
    updated_content = test_file.read_text(encoding="utf-8")
    assert "# comment" not in updated_content
    assert "print('world')" in updated_content
