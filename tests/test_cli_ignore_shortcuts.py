import sys
import argparse
from sourcecombine import main
import pytest

def test_cli_ignore_file_shortcuts(monkeypatch):
    """Test that --ignore and --ig aliases parse correctly and populate args.ignore_file."""
    captured_args = []

    original_parse_args = argparse.ArgumentParser.parse_args

    def mock_parse_args(self, args=None, namespace=None):
        parsed = original_parse_args(self, args, namespace)
        captured_args.append(parsed)
        raise SystemExit(0)

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", mock_parse_args)
    monkeypatch.setattr(sys, "argv", ["sourcecombine.py", "--ignore", "custom1.ignore", "--ig", "custom2.ignore", "."])

    with pytest.raises(SystemExit):
        main()

    assert len(captured_args) == 1
    args = captured_args[0]
    assert args.ignore_file == ["custom1.ignore", "custom2.ignore"]
