import sys
import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Adjust sys.path to include the project root
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import sourcecombine
import utils

def test_render_paired_filename_extended():
    """Verify that paired filename rendering supports expanded placeholders."""
    template = "{{PROJECT_NAME}}/{{DATE}}/{{INDEX}}-{{STEM}}{{SOURCE_EXT}}"
    stem = "main"
    source_path = Path("src/main.cpp")
    relative_dir = Path("src")
    stats = {
        "project_name": "TestProj",
        "date": "2023-10-27"
    }

    # Mock _resolve_metadata_placeholders to avoid full Git/system call if possible,
    # but it's already implemented to use the stats dict.

    rendered = sourcecombine._render_paired_filename(
        template,
        stem,
        source_path,
        None,
        relative_dir,
        stats=stats,
        index=1,
        total=10
    )

    assert rendered == "TestProj/2023-10-27/1-main.cpp"

def test_render_paired_filename_env(monkeypatch):
    """Verify that environment placeholders work in paired filenames."""
    monkeypatch.setenv("BUILD_ID", "12345")
    template = "build-{{ENV:BUILD_ID}}/{{STEM}}.out"
    stem = "app"

    rendered = sourcecombine._render_paired_filename(
        template,
        stem,
        None,
        None,
        Path("."),
        stats={}
    )

    assert rendered == "build-12345/app.out"

def test_render_paired_filename_lang():
    """Verify that {{LANG}} placeholder works in paired filenames."""
    template = "{{LANG}}/{{STEM}}.combined"
    stem = "utils"
    source_path = Path("utils.py")

    rendered = sourcecombine._render_paired_filename(
        template,
        stem,
        source_path,
        None,
        Path("."),
        stats={}
    )

    assert rendered == "python/utils.combined"

def test_process_paired_files_integration(tmp_path, monkeypatch):
    """Integration test for pairing with project placeholders."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "main.cpp").write_text("void main() {}", encoding="utf-8")
    (root / "main.h").write_text("void main();", encoding="utf-8")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    config = utils.DEFAULT_CONFIG.copy()
    config['pairing'] = {
        'enabled': True,
        'source_extensions': ['.cpp'],
        'header_extensions': ['.h'],
        'include_mismatched': False
    }
    config['output'] = {
        'paired_filename_template': "{{PROJECT_NAME}}/{{STEM}}.combined",
        'folder': str(output_dir)
    }

    stats = {
        'project_name': "SuperApp",
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_language': {},
        'top_files': [],
        'git_branch': 'N/A',
        'git_commit_short': 'N/A'
    }

    paired_items = [
        ("main", [root / "main.cpp", root / "main.h"])
    ]

    processor = MagicMock()
    processor.custom_languages = {}

    sourcecombine._process_paired_files(
        paired_items,
        template=config['output']['paired_filename_template'],
        source_exts=('.cpp',),
        header_exts=('.h',),
        root_path=root,
        out_folder=output_dir,
        processor=processor,
        processing_bar=None,
        dry_run=True, # Dry run is enough to check the filename logic
        stats=stats
    )

    # In dry run mode, _process_paired_files logs the mapping.
    # We can verify it didn't crash and maybe check the stats if we didn't mock processor too much.
    # But wait, _process_paired_files actually calls _render_paired_filename to get out_filename.

    # Let's run it for real (dry_run=False) to see if the file is created at the right place.
    # We need a real processor or a good mock.

    real_processor = sourcecombine.FileProcessor(config, config['output'], dry_run=False)

    sourcecombine._process_paired_files(
        paired_items,
        template=config['output']['paired_filename_template'],
        source_exts=('.cpp',),
        header_exts=('.h',),
        root_path=root,
        out_folder=output_dir,
        processor=real_processor,
        processing_bar=None,
        dry_run=False,
        stats=stats
    )

    expected_file = output_dir / "SuperApp" / "main.combined"
    assert expected_file.exists()
