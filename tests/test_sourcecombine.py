import os
import sys
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import should_include


def test_should_include_respects_filters(tmp_path):
    root = tmp_path
    include_file = root / "match.py"
    include_file.write_text("print('ok')", encoding="utf-8")

    exclude_file = root / "skip.tmp"
    exclude_file.write_text("data", encoding="utf-8")

    filter_config = {
        "exclude_filenames": ["*.tmp"],
        "allowed_extensions": (".py",),
        "include_patterns": {"*.py"},
        "min_size_bytes": 0,
        "max_size_bytes": 100,
    }

    assert should_include(include_file, Path(include_file.name), filter_config) is True
    assert should_include(exclude_file, Path(exclude_file.name), filter_config) is False


def test_should_include_respects_size_bounds(tmp_path):
    tiny = tmp_path / "tiny.py"
    tiny.write_text("a", encoding="utf-8")
    big = tmp_path / "big.py"
    big.write_text("x" * 10, encoding="utf-8")

    filter_config = {
        "exclude_filenames": [],
        "allowed_extensions": (".py",),
        "include_patterns": set(),
        "min_size_bytes": 2,
        "max_size_bytes": 5,
    }

    assert should_include(tiny, Path(tiny.name), filter_config) is False
    assert should_include(big, Path(big.name), filter_config) is False

    just_right = tmp_path / "ok.py"
    just_right.write_text("ok", encoding="utf-8")
    assert should_include(just_right, Path(just_right.name), filter_config) is True
