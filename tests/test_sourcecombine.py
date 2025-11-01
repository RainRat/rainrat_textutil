import io
import os
import sys
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import (
    FileProcessor,
    collect_file_paths,
    should_include,
    _pair_files,
)
from utils import compact_whitespace


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


def test_pair_files_logic(tmp_path):
    base = tmp_path
    src = base / "file.cpp"
    hdr = base / "file.h"
    src.write_text("", encoding="utf-8")
    hdr.write_text("", encoding="utf-8")

    result = _pair_files([src, hdr], (".cpp",), (".h",), include_mismatched=False)
    assert result == {"file": [src, hdr]}

    mismatched_src = _pair_files([src], (".cpp",), (".h",), include_mismatched=True)
    assert mismatched_src == {"file": [src]}

    lonely_hdr = _pair_files([hdr], (".cpp",), (".h",), include_mismatched=True)
    assert lonely_hdr == {"file": [hdr]}

    other_hdr = base / "lonely.h"
    other_hdr.write_text("", encoding="utf-8")
    no_pairs = _pair_files([src, other_hdr], (".cpp",), (".h",), include_mismatched=False)
    assert no_pairs == {}

    upper_src = base / "file.CPP"
    upper_hdr = base / "file.H"
    upper_src.write_text("", encoding="utf-8")
    upper_hdr.write_text("", encoding="utf-8")
    mixed_case = _pair_files([upper_src, upper_hdr], (".cpp",), (".h",), include_mismatched=False)
    assert mixed_case == {"file": [upper_src, upper_hdr]}


def test_collect_file_paths_prunes_excluded_folders(tmp_path):
    (tmp_path / "root.txt").write_text("", encoding="utf-8")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "include.py").write_text("", encoding="utf-8")

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("", encoding="utf-8")

    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "app.exe").write_text("", encoding="utf-8")

    nested_build = src_dir / "build"
    nested_build.mkdir()
    (nested_build / "another.o").write_text("", encoding="utf-8")

    collected, _ = collect_file_paths(
        tmp_path,
        recursive=True,
        exclude_folders=[".git", "build"],
    )

    collected_set = {path.relative_to(tmp_path) for path in collected}
    assert Path("root.txt") in collected_set
    assert Path("src/include.py") in collected_set
    assert Path(".git/config") not in collected_set
    assert Path("build/app.exe") not in collected_set
    assert Path("src/build/another.o") not in collected_set


def test_in_place_groups_modify_files_and_output(tmp_path):
    file_path = tmp_path / "sample.txt"
    original = "line   one\n\n\nline two    \n"
    file_path.write_text(original, encoding="utf-8")

    config = {
        "processing": {
            "in_place_groups": {
                "cleanup": {
                    "enabled": True,
                    "options": {
                        "compact_whitespace": True,
                    },
                }
            }
        },
        "output": {
            "header_template": "",
            "footer_template": "",
        },
    }

    processor = FileProcessor(config, config["output"], dry_run=False)
    buffer = io.StringIO()
    processor.process_and_write(file_path, tmp_path, buffer)

    expected = compact_whitespace(original)
    assert file_path.read_text(encoding="utf-8") == expected
    assert buffer.getvalue() == expected


def test_in_place_groups_respect_dry_run(tmp_path):
    file_path = tmp_path / "dry.txt"
    original = "dry run text"
    file_path.write_text(original, encoding="utf-8")

    config = {
        "processing": {
            "in_place_groups": {
                "cleanup": {
                    "enabled": True,
                    "options": {
                        "compact_whitespace": True,
                    },
                }
            }
        },
        "output": {},
    }

    processor = FileProcessor(config, config.get("output"), dry_run=True)
    processor.process_and_write(file_path, tmp_path, None)

    assert file_path.read_text(encoding="utf-8") == original
