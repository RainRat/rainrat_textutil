import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
from sourcecombine import _render_paired_filename
from pathlib import Path
import pytest

def test_paired_filename_with_literal_braces():
    """Verify that literal braces in the template do not cause crashes."""
    template = "file_{{STEM}}_{version}"
    stem = "main"
    rendered = _render_paired_filename(template, stem, None, None, Path("."))
    assert rendered == "file_main_{version}"

def test_paired_filename_with_unknown_placeholder():
    """Verify that unknown placeholders still raise ValueError."""
    template = "file_{{UNKNOWN}}"
    stem = "main"
    with pytest.raises(ValueError) as excinfo:
        _render_paired_filename(template, stem, None, None, Path("."))
    assert "Unknown placeholder '{{UNKNOWN}}'" in str(excinfo.value)

def test_paired_filename_all_placeholders():
    """Verify all supported placeholders are correctly rendered."""
    template = "{{DIR}}/{{DIR_SLUG}}/{{STEM}}{{SOURCE_EXT}}{{HEADER_EXT}}"
    stem = "app"
    source_path = Path("src/app.cpp")
    header_path = Path("include/app.h")
    relative_dir = Path("src")

    rendered = _render_paired_filename(
        template, stem, source_path, header_path, relative_dir
    )
    # DIR=src, DIR_SLUG=src, STEM=app, SOURCE_EXT=.cpp, HEADER_EXT=.h
    assert rendered == "src/src/app.cpp.h"
