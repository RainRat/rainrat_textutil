import io
import os
import sys
from pathlib import Path

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import (
    FileProcessor,
    collect_file_paths,
    find_and_combine_files,
    should_include,
    _pair_files,
    _render_paired_filename,
)
from utils import compact_whitespace


def test_render_paired_filename():
    template = "{{STEM}}-{{SOURCE_EXT}}-{{HEADER_EXT}}.out"
    stem = "my_component"
    source_path = Path("/tmp/my_component.cpp")
    header_path = Path("/tmp/my_component.h")

    rendered = _render_paired_filename(
        template, stem, source_path, header_path, relative_dir=Path('.')
    )
    assert rendered == "my_component-.cpp-.h.out"

    rendered_no_header = _render_paired_filename(
        template, stem, source_path, None, relative_dir=Path('.')
    )
    assert rendered_no_header == "my_component-.cpp-.out"


def test_render_paired_filename_includes_dir_placeholders():
    template = "{{DIR}}|{{DIR_SLUG}}|{{STEM}}"
    relative_dir = Path("src") / "My Dir" / "Sub.Dir"
    source_path = Path("/project") / relative_dir / "Example.cpp"
    header_path = Path("/project") / relative_dir / "Example.h"

    rendered = _render_paired_filename(
        template,
        "Example",
        source_path,
        header_path,
        relative_dir=relative_dir,
    )
    assert rendered == "src/My Dir/Sub.Dir|src/my-dir/sub.dir|Example"

    root_source = Path("/project/Example.cpp")
    root_rendered = _render_paired_filename(
        template,
        "RootExample",
        root_source,
        None,
        relative_dir=Path('.'),
    )
    assert root_rendered == ".|root|RootExample"


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


def test_should_include_respects_relative_path_globs(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    main_py = src_dir / "main.py"
    main_py.touch()

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_main_py = tests_dir / "test_main.py"
    test_main_py.touch()

    filter_config = {
        "exclude_filenames": ["tests/*"],
        "allowed_extensions": (".py",),
        "include_patterns": set(),
        "min_size_bytes": 0,
        "max_size_bytes": 100,
    }

    assert (
        should_include(
            main_py, main_py.relative_to(tmp_path), filter_config
        )
        is True
    )
    assert (
        should_include(
            test_main_py,
            test_main_py.relative_to(tmp_path),
            filter_config,
        )
        is False
    )


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
