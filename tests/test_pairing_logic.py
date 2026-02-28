import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import (
    FileProcessor,
    _pair_files,
    _process_paired_files,
)

def test_pair_files_logic(tmp_path):
    base = tmp_path
    src = base / "file.cpp"
    hdr = base / "file.h"
    src.write_text("", encoding="utf-8")
    hdr.write_text("", encoding="utf-8")

    result = _pair_files(
        [src, hdr], (".cpp",), (".h",), include_mismatched=False, root_path=base
    )
    assert result == {Path("file"): [src, hdr]}

    mismatched_src = _pair_files(
        [src], (".cpp",), (".h",), include_mismatched=True, root_path=base
    )
    assert mismatched_src == {Path("file"): [src]}

    lonely_hdr = _pair_files(
        [hdr], (".cpp",), (".h",), include_mismatched=True, root_path=base
    )
    assert lonely_hdr == {Path("file"): [hdr]}

    other_hdr = base / "lonely.h"
    other_hdr.write_text("", encoding="utf-8")
    no_pairs = _pair_files(
        [src, other_hdr], (".cpp",), (".h",), include_mismatched=False, root_path=base
    )
    assert no_pairs == {}

    upper_src = base / "file.CPP"
    upper_hdr = base / "file.H"
    upper_src.write_text("", encoding="utf-8")
    upper_hdr.write_text("", encoding="utf-8")
    mixed_case = _pair_files(
        [upper_src, upper_hdr],
        (".cpp",),
        (".h",),
        include_mismatched=False,
        root_path=base,
    )
    assert mixed_case == {Path("file"): [upper_src, upper_hdr]}


def test_pair_files_prefers_extension_order(tmp_path):
    base = tmp_path
    src_cpp = base / "file.cpp"
    src_cc = base / "file.cc"
    hdr_h = base / "file.h"
    hdr_hpp = base / "file.hpp"

    for path in (src_cpp, src_cc, hdr_h, hdr_hpp):
        path.write_text("", encoding="utf-8")

    result = _pair_files(
        [hdr_h, src_cc, src_cpp, hdr_hpp],
        (".cpp", ".cc"),
        (".hpp", ".h"),
        include_mismatched=False,
        root_path=base,
    )

    assert result == {Path("file"): [src_cpp, hdr_hpp]}


def test_pair_files_respects_relative_directories(tmp_path):
    root = tmp_path
    feature_dir = root / "src" / "feature"
    other_dir = root / "src" / "other"
    header_dir = root / "include" / "feature"
    for path in (feature_dir, other_dir, header_dir):
        path.mkdir(parents=True, exist_ok=True)

    feature_src = feature_dir / "main.cpp"
    other_src = other_dir / "main.cpp"
    feature_hdr = header_dir / "main.h"

    for path in (feature_src, other_src, feature_hdr):
        path.write_text("", encoding="utf-8")

    result = _pair_files(
        [feature_src, feature_hdr, other_src],
        (".cpp",),
        (".h",),
        include_mismatched=False,
        root_path=root,
    )

    assert result == {Path("src/feature/main"): [feature_src, feature_hdr]}


def test_pair_files_pairs_unique_cross_folder_files(tmp_path):
    root = tmp_path
    src_dir = root / "src"
    include_dir = root / "include"
    src_dir.mkdir()
    include_dir.mkdir()

    source = src_dir / "utils.cpp"
    header = include_dir / "utils.h"

    source.write_text("", encoding="utf-8")
    header.write_text("", encoding="utf-8")

    result = _pair_files(
        [source, header],
        (".cpp",),
        (".h",),
        include_mismatched=False,
        root_path=root,
    )

    assert result == {Path("src/utils"): [source, header]}


def test_pair_files_handles_colliding_names_in_separate_modules(tmp_path):
    root = tmp_path

    foo_src = root / "src" / "foo" / "util.cpp"
    foo_hdr = root / "include" / "foo" / "util.h"
    bar_src = root / "src" / "bar" / "util.cpp"
    bar_hdr = root / "include" / "bar" / "util.h"

    for path in (foo_src, foo_hdr, bar_src, bar_hdr):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    result = _pair_files(
        [foo_src, foo_hdr, bar_src, bar_hdr],
        (".cpp",),
        (".h",),
        include_mismatched=False,
        root_path=root,
    )

    assert result == {
        Path("src/foo/util"): [foo_src, foo_hdr],
        Path("src/bar/util"): [bar_src, bar_hdr],
    }


def test_process_paired_files_writes_outputs(tmp_path):
    root = tmp_path / "project"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)

    source_path = src_dir / "example.cpp"
    header_path = src_dir / "example.hpp"
    source_path.write_text("src", encoding="utf-8")
    header_path.write_text("hdr", encoding="utf-8")

    config = {"processing": {}, "output": {"header_template": "", "footer_template": ""}}
    processor = FileProcessor(config, config["output"], dry_run=False)

    pairs = {"example": [source_path, header_path]}
    out_folder = root / "out"

    _process_paired_files(
        pairs,
        template="{{DIR_SLUG}}/{{STEM}}{{SOURCE_EXT}}{{HEADER_EXT}}.out",
        source_exts=(".cpp",),
        header_exts=(".hpp",),
        root_path=root,
        out_folder=out_folder,
        processor=processor,
        processing_bar=None,
        dry_run=False,
    )

    output_file = out_folder / "src/example.cpp.hpp.out"
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "srchdr"

def test_pair_files_unrooted_path_value_error_branch():
    from pathlib import Path
    from sourcecombine import _pair_files
    root_path = Path("/root")
    filtered_paths = [Path("/other/file.cpp")]

    result = _pair_files(filtered_paths, (), (), False, root_path=root_path)
    assert result == {}
