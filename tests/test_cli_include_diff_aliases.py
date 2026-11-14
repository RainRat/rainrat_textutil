import sys
from unittest.mock import patch
import sourcecombine


def test_cli_alias_inc_diff(tmp_path, monkeypatch):
    """Verify that --inc-diff acts as a shortcut alias for --include-diff."""
    test_file = tmp_path / "app.py"
    test_file.write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    test_args = ["sourcecombine.py", "--inc-diff", "-d", "."]
    with patch.object(sys, "argv", test_args):
        with patch.object(sourcecombine, "find_and_combine_files") as mock_combine:
            mock_combine.return_value = {}
            sourcecombine.main()
            assert mock_combine.called
            config = mock_combine.call_args[0][0]
            assert config["output"].get("include_diff") is True


def test_cli_alias_git_diff_overview(tmp_path, monkeypatch):
    """Verify that --git-diff-overview acts as a shortcut alias for --include-diff."""
    test_file = tmp_path / "app.py"
    test_file.write_text("print('hello')\n", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    test_args = ["sourcecombine.py", "--git-diff-overview", "-d", "."]
    with patch.object(sys, "argv", test_args):
        with patch.object(sourcecombine, "find_and_combine_files") as mock_combine:
            mock_combine.return_value = {}
            sourcecombine.main()
            assert mock_combine.called
            config = mock_combine.call_args[0][0]
            assert config["output"].get("include_diff") is True
