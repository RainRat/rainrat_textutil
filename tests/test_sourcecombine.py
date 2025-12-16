import io
import logging
import os
import sys
import subprocess
import types
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

pyperclip_stub = types.SimpleNamespace(copy=lambda _text: None, paste=lambda: None)
sys.modules.setdefault("pyperclip", pyperclip_stub)

import sourcecombine
from sourcecombine import (
    FileProcessor,
    collect_file_paths,
    find_and_combine_files,
    should_include,
    _pair_files,
    _process_paired_files,
    _progress_enabled,
)
from utils import compact_whitespace


def test_progress_enabled_behavior(monkeypatch, caplog):
    monkeypatch.delenv("CI", raising=False)

    with caplog.at_level(logging.INFO):
        assert _progress_enabled(False) is True

    with caplog.at_level(logging.DEBUG):
        assert _progress_enabled(False) is False


def test_progress_disabled_for_dry_run(monkeypatch, caplog):
    monkeypatch.delenv("CI", raising=False)

    with caplog.at_level(logging.INFO):
        assert _progress_enabled(True) is False

    with caplog.at_level(logging.DEBUG):
        assert _progress_enabled(True) is False


def test_progress_disabled_in_ci(monkeypatch, caplog):
    monkeypatch.setenv("CI", "1")

    with caplog.at_level(logging.INFO):
        assert _progress_enabled(False) is False


def test_should_include_respects_filters(tmp_path):
    root = tmp_path
    include_file = root / "match.py"
    include_file.write_text("print('ok')", encoding="utf-8")

    exclude_file = root / "skip.tmp"
    exclude_file.write_text("data", encoding="utf-8")

    filter_opts = {
        "exclusions": {"filenames": ["*.tmp"]},
        "inclusion_groups": {"py": {"enabled": True, "filenames": ["*.py"]}},
        "min_size_bytes": 0,
        "max_size_bytes": 100,
    }
    search_opts = {"effective_allowed_extensions": (".py",)}

    assert (
        should_include(
            include_file, Path(include_file.name), filter_opts, search_opts
        )
        is True
    )
    assert (
        should_include(
            exclude_file, Path(exclude_file.name), filter_opts, search_opts
        )
        is False
    )


def test_should_include_respects_relative_path_globs(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    main_py = src_dir / "main.py"
    main_py.touch()

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_main_py = tests_dir / "test_main.py"
    test_main_py.touch()

    filter_opts = {
        "exclusions": {"filenames": ["tests/*"]},
        "inclusion_groups": {},
        "min_size_bytes": 0,
        "max_size_bytes": 100,
    }
    search_opts = {"effective_allowed_extensions": (".py",)}

    assert (
        should_include(
            main_py, main_py.relative_to(tmp_path), filter_opts, search_opts
        )
        is True
    )
    assert (
        should_include(
            test_main_py,
            test_main_py.relative_to(tmp_path),
            filter_opts,
            search_opts,
        )
        is False
    )


def test_should_include_respects_size_bounds(tmp_path):
    tiny = tmp_path / "tiny.py"
    tiny.write_text("a", encoding="utf-8")
    big = tmp_path / "big.py"
    big.write_text("x" * 10, encoding="utf-8")

    filter_opts = {
        "exclusions": {"filenames": []},
        "inclusion_groups": {},
        "min_size_bytes": 2,
        "max_size_bytes": 5,
    }
    search_opts = {"effective_allowed_extensions": (".py",)}

    assert (
        should_include(tiny, Path(tiny.name), filter_opts, search_opts) is False
    )
    assert should_include(big, Path(big.name), filter_opts, search_opts) is False

    just_right = tmp_path / "ok.py"
    just_right.write_text("ok", encoding="utf-8")
    assert (
        should_include(just_right, Path(just_right.name), filter_opts, search_opts)
        is True
    )


def test_should_include_skips_binary_when_requested(tmp_path):
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\x00\x01binary data")

    text_file = tmp_path / "note.txt"
    text_file.write_text("hello", encoding="utf-8")

    filter_opts = {
        "skip_binary": True,
        "exclusions": {"filenames": []},
        "inclusion_groups": {},
        "min_size_bytes": 0,
        "max_size_bytes": 0,
    }
    search_opts = {"effective_allowed_extensions": (".bin", ".txt")}

    assert should_include(binary, Path(binary.name), filter_opts, search_opts) is False
    assert should_include(text_file, Path(text_file.name), filter_opts, search_opts) is True


def test_should_include_treats_zero_max_size_as_unlimited(tmp_path):
    big = tmp_path / "big.py"
    big.write_text("x" * 100, encoding="utf-8")

    filter_opts = {
        "exclusions": {"filenames": []},
        "inclusion_groups": {},
        "min_size_bytes": 0,
        "max_size_bytes": 0,
    }
    search_opts = {"effective_allowed_extensions": (".py",)}

    assert should_include(big, Path(big.name), filter_opts, search_opts) is True


def test_max_size_placeholder_writes_entry(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    small = project_root / "small.txt"
    small.write_text("ok", encoding="utf-8")
    big = project_root / "big.txt"
    big.write_text("x" * 10, encoding="utf-8")

    output_path = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {"max_size_bytes": 5},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "max_size_placeholder": "[SKIPPED {{FILENAME}}]",
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    content = output_path.read_text(encoding="utf-8")
    assert "[SKIPPED big.txt]" in content
    assert "ok" in content


def test_clipboard_mode_copies_output(monkeypatch, tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    sample = project_root / "sample.txt"
    sample.write_text("copied", encoding="utf-8")

    output_path = tmp_path / "unused.txt"
    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "output": {"file": os.fspath(output_path), "header_template": "", "footer_template": ""},
    }

    copied = {}

    def _fake_copy(text):
        copied["text"] = text

    monkeypatch.setattr(sys.modules["pyperclip"], "copy", _fake_copy)

    find_and_combine_files(config, output_path, dry_run=False, clipboard=True)

    assert copied["text"] == "copied"
    assert not output_path.exists()


def test_clipboard_mode_rejects_pairing(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / "one.cpp").write_text("one", encoding="utf-8")
    (project_root / "one.hpp").write_text("two", encoding="utf-8")

    output_path = tmp_path / "paired"
    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "pairing": {"enabled": True, "source_extensions": [".cpp"], "header_extensions": [".hpp"]},
        "output": {"folder": os.fspath(output_path)},
    }

    with pytest.raises(sourcecombine.InvalidConfigError):
        find_and_combine_files(config, output_path, dry_run=False, clipboard=True)


def test_output_file_required_without_pairing_or_clipboard(tmp_path):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / "one.txt").write_text("data", encoding="utf-8")

    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {},
        "pairing": {"enabled": False},
        "output": {"file": None, "header_template": "", "footer_template": ""},
    }

    with pytest.raises(sourcecombine.InvalidConfigError):
        find_and_combine_files(config, output_path=None, dry_run=False, clipboard=False)


def test_verbose_logs_when_placeholder_written(tmp_path, caplog):
    project_root = tmp_path / "proj"
    project_root.mkdir()
    project_root.joinpath("small.txt").write_text("ok", encoding="utf-8")
    big_file = project_root / "big.txt"
    big_file.write_text("x" * 10, encoding="utf-8")

    output_path = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {"max_size_bytes": 5},
        "processing": {},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
            "max_size_placeholder": "[SKIPPED {{FILENAME}}]",
        },
    }

    with caplog.at_level(logging.DEBUG):
        find_and_combine_files(config, output_path, dry_run=False)

    assert any(
        "File exceeds max size; writing placeholder" in record.message
        and "big.txt" in record.message
        for record in caplog.records
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


def test_cli_missing_config_produces_friendly_error():
    script = Path(__file__).resolve().parent.parent / "sourcecombine.py"
    result = subprocess.run(
        [sys.executable, os.fspath(script), "does_not_exist.yml"],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "Could not find the configuration file 'does_not_exist.yml'" in result.stderr
    assert "Traceback" not in result.stderr


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


def test_pair_files_pairs_unique_cross_directory_files(tmp_path):
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


def test_collect_file_paths_counts_exclusions_correctly(tmp_path):
    root = tmp_path / "project"
    root.mkdir()

    (root / "keep.txt").write_text("", encoding="utf-8")

    build_dir = root / "build"
    build_dir.mkdir()
    (build_dir / "skip.bin").write_text("", encoding="utf-8")

    src_dir = root / "src"
    src_dir.mkdir()
    (src_dir / "include.py").write_text("", encoding="utf-8")

    nested_build = src_dir / "build"
    nested_build.mkdir()
    (nested_build / "ignored.o").write_text("", encoding="utf-8")

    git_dir = root / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("", encoding="utf-8")

    recursive_collected, _, recursive_excluded = collect_file_paths(
        root,
        recursive=True,
        exclude_folders=["build", ".git"],
    )

    assert recursive_excluded == 3
    recursive_set = {path.relative_to(root) for path in recursive_collected}
    assert Path("keep.txt") in recursive_set
    assert Path("src/include.py") in recursive_set
    assert Path("build/skip.bin") not in recursive_set
    assert Path("src/build/ignored.o") not in recursive_set
    assert Path(".git/config") not in recursive_set

    nonrecursive_collected, _, nonrecursive_excluded = collect_file_paths(
        root,
        recursive=False,
        exclude_folders=["build", ".git"],
    )

    assert nonrecursive_excluded == 2
    assert {path.relative_to(root) for path in nonrecursive_collected} == {
        Path("keep.txt")
    }


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

    collected, _, _ = collect_file_paths(
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


def test_collect_file_paths_handles_oserror(monkeypatch, tmp_path, caplog):
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    (root_dir / "keep.txt").write_text("", encoding="utf-8")

    def _raise_os_error(*_args, **_kwargs):
        raise OSError("permission denied")

    monkeypatch.setattr(sourcecombine.os, "walk", _raise_os_error)

    with caplog.at_level(logging.WARNING):
        collected, root_path, excluded_count = collect_file_paths(
            root_dir, recursive=True, exclude_folders=[]
        )

    assert collected == []
    assert root_path == root_dir
    assert excluded_count == 0
    assert "Error while traversing" in caplog.text


def test_apply_in_place_updates_files_and_output(tmp_path):
    file_path = tmp_path / "sample.txt"
    original = "line   one\n\n\nline two    \n"
    file_path.write_text(original, encoding="utf-8")

    config = {
        "processing": {
            "apply_in_place": True,
            "compact_whitespace": True,
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


def test_apply_in_place_without_backups(tmp_path):
    file_path = tmp_path / "nobackups.txt"
    original = "line with   gaps"
    file_path.write_text(original, encoding="utf-8")

    output_path = tmp_path / "combined.txt"
    config = {
        "search": {"root_folders": [os.fspath(tmp_path)], "recursive": True},
        "filters": {},
        "processing": {
            "apply_in_place": True,
            "compact_whitespace": True,
            "create_backups": False,
        },
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    expected = compact_whitespace(original)
    assert file_path.read_text(encoding="utf-8") == expected
    assert output_path.read_text(encoding="utf-8") == expected
    assert not (tmp_path / "nobackups.txt.bak").exists()


def test_apply_in_place_creates_backups_by_default(tmp_path):
    file_path = tmp_path / "backup.txt"
    original = "needs cleanup\t\t\n"
    file_path.write_text(original, encoding="utf-8")

    config = {
        "processing": {
            "apply_in_place": True,
            "compact_whitespace": True,
        },
        "output": {},
    }

    processor = FileProcessor(config, config.get("output"), dry_run=False)
    processor.process_and_write(file_path, tmp_path, io.StringIO())

    backup_path = tmp_path / "backup.txt.bak"
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == original


def test_apply_in_place_respects_dry_run(tmp_path):
    file_path = tmp_path / "dry.txt"
    original = "dry run text"
    file_path.write_text(original, encoding="utf-8")

    config = {
        "processing": {
            "apply_in_place": True,
            "compact_whitespace": True,
        },
        "output": {},
    }

    processor = FileProcessor(config, config.get("output"), dry_run=True)
    processor.process_and_write(file_path, tmp_path, None)

    assert file_path.read_text(encoding="utf-8") == original
    assert not (tmp_path / "dry.txt.bak").exists()


def test_apply_in_place_can_disable_backups(tmp_path):
    file_path = tmp_path / "nobackup.txt"
    file_path.write_text("content", encoding="utf-8")

    config = {
        "processing": {
            "apply_in_place": True,
            "create_backups": False,
            "regex_replacements": [
                {"pattern": "content", "replacement": "updated"}
            ],
        },
        "output": {},
    }

    processor = FileProcessor(config, config.get("output"), dry_run=False)
    processor.process_and_write(file_path, tmp_path, io.StringIO())

    assert (tmp_path / "nobackup.txt.bak").exists() is False
    assert file_path.read_text(encoding="utf-8") == "updated"


def test_find_and_combine_skips_backup_files(tmp_path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    source_path = project_root / "notes.txt"
    source_path.write_text("original", encoding="utf-8")
    backup_path = project_root / "notes.txt.bak"
    backup_path.write_text("backup", encoding="utf-8")

    output_path = tmp_path / "combined.txt"
    config = {
        "search": {"root_folders": [os.fspath(project_root)], "recursive": True},
        "filters": {},
        "processing": {"apply_in_place": True},
        "output": {
            "file": os.fspath(output_path),
            "header_template": "",
            "footer_template": "",
        },
    }

    find_and_combine_files(config, output_path, dry_run=False)

    assert output_path.read_text(encoding="utf-8") == "original"
    assert (project_root / "notes.txt.bak.bak").exists() is False


def test_main_overrides_output_file(monkeypatch, tmp_path):
    root_folder = tmp_path / "root"
    root_folder.mkdir()
    config_path = tmp_path / "config.yml"
    override_output = tmp_path / "override.txt"
    config_path.write_text(
        yaml.safe_dump(
            {
                "search": {"root_folders": [os.fspath(root_folder)]},
                "pairing": {"enabled": False},
                "output": {"file": os.fspath(tmp_path / "config_output.txt")},
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_find_and_combine_files(cfg, output_path, **_kwargs):
        captured["config_output"] = cfg["output"].copy()
        captured["output_path"] = output_path
        return {}

    monkeypatch.setattr(sourcecombine, "find_and_combine_files", fake_find_and_combine_files)
    monkeypatch.setattr(
        sys, "argv", ["prog", os.fspath(config_path), "--output", os.fspath(override_output)]
    )

    sourcecombine.main()

    assert captured["output_path"] == os.fspath(override_output)
    assert captured["config_output"]["file"] == os.fspath(override_output)


def test_main_overrides_output_folder_in_pairing_mode(monkeypatch, tmp_path):
    root_folder = tmp_path / "root"
    root_folder.mkdir()
    config_path = tmp_path / "config.yml"
    override_output = tmp_path / "paired_outputs"
    config_path.write_text(
        yaml.safe_dump(
            {
                "search": {"root_folders": [os.fspath(root_folder)]},
                "pairing": {"enabled": True},
                "output": {"folder": os.fspath(tmp_path / "config_outputs")},
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_find_and_combine_files(cfg, output_path, **_kwargs):
        captured["config_output"] = cfg["output"].copy()
        captured["output_path"] = output_path
        return {}

    monkeypatch.setattr(sourcecombine, "find_and_combine_files", fake_find_and_combine_files)
    monkeypatch.setattr(
        sys, "argv", ["prog", os.fspath(config_path), "--output", os.fspath(override_output)]
    )

    sourcecombine.main()

    assert captured["output_path"] == os.fspath(override_output)
    assert captured["config_output"]["folder"] == os.fspath(override_output)
