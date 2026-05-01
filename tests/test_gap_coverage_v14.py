import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import json
import logging
import pytest
from pathlib import PurePath, Path
from sourcecombine import _parse_combined_content, _pair_files, should_include, extract_files, _process_paired_files, FileProcessor
from utils import validate_config

def test_parse_combined_content_json_dict():
    """Cover branch where JSON is a dict instead of a list (4179->exit)."""
    content = json.dumps({"key": "value"})
    assert _parse_combined_content(content) == []

def test_parse_combined_content_json_invalid_entries():
    """Cover branch where JSON list contains invalid entries (4181->4180)."""
    content = json.dumps([
        {"path": "only_path"},
        {"content": "only_content"},
        "not_a_dict"
    ])
    # Now that we support entries with only 'path', 'only_path' is valid.
    # 'only_content' and 'not_a_dict' are still invalid.
    result = _parse_combined_content(content)
    assert len(result) == 1
    assert result[0][0] == "only_path"

def test_parse_combined_content_xml_empty():
    """Cover branch where XML is valid but contains no files (4258->4264)."""
    content = "<repository></repository>"
    assert _parse_combined_content(content) == []

def test_parse_combined_content_markdown_no_header():
    """Cover branch where Markdown has code block but no preceding header (4279->4283)."""
    content = "Some text\n\n```python\nprint('hello')\n```"
    assert _parse_combined_content(content) == []

def test_pair_files_src_is_hdr(tmp_path):
    """Cover branches where src and hdr might be the same (1204->1206 and 1232->1235)."""
    root = tmp_path / "project"
    root.mkdir()

    # overlap source and header exts
    source_exts = [".c"]
    header_exts = [".c"]

    # Case for Pass 1: stem matches exactly
    f1 = root / "main.c"
    f1.write_text("content")
    pairs1 = _pair_files([f1], source_exts, header_exts, include_mismatched=False, root_path=root)
    assert len(pairs1) == 1
    assert len(pairs1[0][1]) == 1

    # Case for Pass 2: stem matches after truncation
    f2 = root / "src" / "other.c"
    f2.parent.mkdir()
    f2.write_text("content")
    pairs2 = _pair_files([f2], source_exts, header_exts, include_mismatched=False, root_path=root)
    assert len(pairs2) == 1
    assert len(pairs2[0][1]) == 1

def test_should_include_virtual_content_binary_check():
    """Cover branch checking binary for virtual content (630->639)."""
    opts = {'skip_binary': True}
    search_opts = {}
    rel_path = PurePath("test.txt")

    # Case 1: virtual_content as bytes, is binary
    assert should_include(None, rel_path, filter_opts=opts, search_opts=search_opts, virtual_content=b"\x00") is False

    # Case 2: virtual_content as str, is binary
    assert should_include(None, rel_path, filter_opts=opts, search_opts=search_opts, virtual_content="\x00") is False

    # Case 3: virtual_content is None, should go to 639
    assert should_include(None, rel_path, filter_opts=opts, search_opts=search_opts, virtual_content=None) is True

def test_should_include_disabled_group():
    """Cover branch 617->616: inclusion_groups with disabled group."""
    opts = {
        'inclusion_groups': {
            'disabled': {'enabled': False, 'filenames': ['*.py']}
        }
    }
    search_opts = {}
    rel_path = PurePath("test.py")
    assert should_include(None, rel_path, filter_opts=opts, search_opts=search_opts) is True

def test_validate_filters_none_values():
    """Cover gaps in utils.py _validate_filters_section (555->553, 578->586, 587->602)."""
    config = {
        'search': {'root_folders': ['.']},
        'filters': {
            'modified_since': None,
            'modified_until': None,
            'exclusions': None,
            'inclusion_groups': None
        },
        'processing': {},
        'pairing': {},
        'output': {}
    }
    validate_config(config, defaults={})
    assert config['filters']['modified_since'] is None

def test_extract_files_limit_reached(tmp_path):
    """Cover branch where extraction limit is reached (4368->4337)."""
    content = "--- a.txt ---\na\n--- end a.txt ---\n--- b.txt ---\nb\n--- end b.txt ---"
    out = tmp_path / "out"
    stats = extract_files(content, out, limit=1)
    assert stats['total_files'] == 1

def test_process_paired_files_overwrite_warning(tmp_path, caplog):
    """Cover branch 1318->1320: pairing output overwrites input file."""
    root = tmp_path / "root"
    root.mkdir()
    src = root / "main.c"
    src.write_text("int main() {}")
    out_folder = root

    import utils
    config = json.loads(json.dumps(utils.DEFAULT_CONFIG))
    output_opts = config['output']
    output_opts['paired_filename_template'] = "main.c" # Collision!
    processor = FileProcessor(config, output_opts)

    paired_items = [("main", [src])]
    source_exts = [".c"]
    header_exts = [".h"]

    with caplog.at_level(logging.WARNING):
        _process_paired_files(
            paired_items,
            template="main.c",
            source_exts=source_exts,
            header_exts=header_exts,
            root_path=root,
            out_folder=out_folder,
            processor=processor,
            processing_bar=None,
            dry_run=False
        )

    assert "would overwrite one of its input files" in caplog.text
