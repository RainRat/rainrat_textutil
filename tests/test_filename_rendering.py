import os
import sys
from pathlib import Path, PureWindowsPath
import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import _render_paired_filename, _slugify_relative_dir

def test_render_paired_filename_placeholders():
    template = "{{DIR}}|{{DIR_SLUG}}|{{STEM}}{{SOURCE_EXT}}{{HEADER_EXT}}"
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
    assert rendered == "src/My Dir/Sub.Dir|src/my-dir/sub.dir|Example.cpp.h"

    root_source = Path("/project/Example.cpp")
    root_rendered = _render_paired_filename(
        template,
        "RootExample",
        root_source,
        None,
        relative_dir=Path('.'),
    )
    assert root_rendered == ".|root|RootExample.cpp"


def test_render_paired_filename_windows_dirs():
    template = "{{DIR}}|{{DIR_SLUG}}|{{STEM}}{{SOURCE_EXT}}{{HEADER_EXT}}"
    relative_dir = PureWindowsPath("src\\My Dir\\Sub.Dir")
    source_path = Path("C:/project/src/My Dir/Sub.Dir/Example.cpp")
    header_path = Path("C:/project/src/My Dir/Sub.Dir/Example.hpp")

    rendered = _render_paired_filename(
        template,
        "Example",
        source_path,
        header_path,
        relative_dir=relative_dir,
    )

    assert rendered == "src/My Dir/Sub.Dir|src/my-dir/sub.dir|Example.cpp.hpp"


def test_slugify_relative_dir_basics():
    assert _slugify_relative_dir("foo/bar") == "foo/bar"
    assert _slugify_relative_dir("Foo Bar") == "foo-bar"
    assert _slugify_relative_dir("root") == "root"
    assert _slugify_relative_dir("") == "root"
    assert _slugify_relative_dir(".") == "root"


def test_slugify_relative_dir_unnamed():
    # "!!!" -> "---" -> stripped to "" -> "unnamed"
    assert _slugify_relative_dir("!!!") == "unnamed"
    assert _slugify_relative_dir("foo/!!!/bar") == "foo/unnamed/bar"


def test_render_paired_filename_invalid_placeholder():
    template = "{{BAD_PLACEHOLDER}}"
    with pytest.raises(ValueError) as excinfo:
        _render_paired_filename(
            template,
            "stem",
            Path("src.cpp"),
            Path("hdr.h"),
            Path("dir")
        )
    assert "Unknown placeholder '{{BAD_PLACEHOLDER}}'" in str(excinfo.value)
