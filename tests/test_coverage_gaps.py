import os
import sys
import logging
import shutil
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from utils import (
    validate_config,
    InvalidConfigError,
    _validate_pairing_section,
    load_yaml_config,
    compact_whitespace,
    _validate_regex_list,
    _validate_glob_list,
    process_content,
    validate_glob_pattern,
    DEFAULT_CONFIG,
)
from sourcecombine import (
    _update_file_stats,
    _group_paths_by_stem_suffix,
    find_and_combine_files,
    _get_rel_path,
    collect_file_paths,
    _process_paired_files,
    FileProcessor,
    main,
)

def test_validate_regex_list_not_a_list():
    with pytest.raises(InvalidConfigError, match="'test' must be a list"):
        _validate_regex_list("not a list", "test", None)

def test_validate_regex_list_item_not_a_dict():
    with pytest.raises(InvalidConfigError, match="Item 0 in 'test' must be a dictionary"):
        _validate_regex_list(["not a dict"], "test", None)

def test_validate_glob_list_not_a_list():
    with pytest.raises(InvalidConfigError, match="'test' must be a list"):
        _validate_glob_list("not a list", "test")

def test_validate_glob_list_none():
    _validate_glob_list(None, "test")

def test_validate_filters_section_not_a_dict():
    config = {"filters": "not a dict"}
    validate_config(config)

def test_validate_processing_section_not_a_dict():
    config = {"processing": "not a dict"}
    validate_config(config)

def test_validate_processing_section_non_bool():
    config = {"processing": {"apply_in_place": "not a bool"}}
    with pytest.raises(InvalidConfigError, match="'processing.apply_in_place' must be true or false"):
        validate_config(config)

    config = {"processing": {"create_backups": "not a bool"}}
    with pytest.raises(InvalidConfigError, match="'processing.create_backups' must be true or false"):
        validate_config(config)

def test_validate_config_missing_nested_key():
    config = {"search": {}}
    nested_required = {"search": ["root_folders"]}
    with pytest.raises(InvalidConfigError, match="'search' section is missing keys: root_folders"):
        validate_config(config, nested_required=nested_required)

def test_process_content_regex_missing_fields():
    text = "hello world"
    options = {
        "regex_replacements": [
            {"pattern": "hello"},
            {"replacement": "bye"},
        ]
    }
    assert process_content(text, options) == text

def test_process_content_compact_whitespace_unknown_key():
    text = "a   b"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "unknown": True,
            "compact_space_runs": True
        }
    }
    assert process_content(text, options) == "a  b"

def test_process_content_compact_whitespace_all_unknown():
    text = "a   b"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "unknown": True
        }
    }
    assert process_content(text, options) == "a  b"

def test_process_content_compact_whitespace_with_none():
    text = "a   b"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "compact_space_runs": None
        }
    }
    assert process_content(text, options) == "a  b"

def test_validate_glob_pattern_mismatched_brackets(caplog):
    with caplog.at_level(logging.WARNING):
        validate_glob_pattern("file[a-z.txt", context="test")
    assert "mismatched brackets" in caplog.text

def test_get_rel_path_fallback():
    p = Path("/outside/file.txt")
    root = Path("/app/project")
    assert _get_rel_path(p, root) == p

def test_find_and_combine_with_explicit_dir(tmp_path):
    tmp_dir = tmp_path / "explicit_dir"
    tmp_dir.mkdir()

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(tmp_path)], 'recursive': True}

    stats = find_and_combine_files(
        config,
        output_path=str(tmp_path / "out.txt"),
        explicit_files=[tmp_dir]
    )

    assert stats['total_files'] == 0

def test_collect_file_paths_file(tmp_path):
    tmp_file = tmp_path / "test.txt"
    tmp_file.write_text("content", encoding="utf-8")

    progress = MagicMock()
    paths, root, excluded = collect_file_paths(
        str(tmp_file), recursive=True, exclude_folders=[], progress=progress
    )

    assert paths == [tmp_file]
    assert root == tmp_path
    progress.update.assert_called_once_with(1)

def test_collect_file_paths_oserror(tmp_path):
    root = tmp_path / "restricted"
    root.mkdir()

    with patch('pathlib.Path.iterdir', side_effect=OSError("Access denied")):
        paths, root_out, excluded = collect_file_paths(
            str(root), recursive=False, exclude_folders=[]
        )

    assert paths == []
    assert excluded == 0

def test_process_paired_files_full_coverage(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    src = root / "file.c"
    src.write_text("content")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['pairing']['enabled'] = True
    config['output']['max_size_placeholder'] = "Too big: {{FILENAME}}"
    config['output']['global_header_template'] = "GLOBAL HEADER"
    config['output']['global_footer_template'] = "GLOBAL FOOTER"

    processor = FileProcessor(config, config['output'], dry_run=True)

    paired_paths = {
        "file": [src]
    }

    _process_paired_files(
        paired_paths,
        template="{{STEM}}.combined",
        source_exts=[".c"],
        header_exts=[".h"],
        root_path=root,
        out_folder=None,
        processor=processor,
        processing_bar=None,
        dry_run=True
    )

    processor.dry_run = False
    processor.estimate_tokens = True
    _process_paired_files(
        paired_paths,
        template="{{STEM}}.combined",
        source_exts=[".c"],
        header_exts=[".h"],
        root_path=root,
        out_folder=None,
        processor=processor,
        processing_bar=None,
        dry_run=False,
        estimate_tokens=True
    )

    processor.estimate_tokens = False
    _process_paired_files(
        paired_paths,
        template="{{STEM}}.combined",
        source_exts=[".c"],
        header_exts=[".h"],
        root_path=root,
        out_folder=None,
        processor=processor,
        processing_bar=None,
        dry_run=False,
        estimate_tokens=False,
        global_header="HEADER",
        global_footer="FOOTER"
    )

    progress = MagicMock()
    _process_paired_files(
        paired_paths,
        template="{{STEM}}.combined",
        source_exts=[".c"],
        header_exts=[".h"],
        root_path=root,
        out_folder=None,
        processor=processor,
        processing_bar=progress,
        dry_run=False,
        estimate_tokens=False,
        size_excluded=[src]
    )
    progress.update.assert_called()

def test_limit_pass_full_coverage(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    f1 = root / "f1.txt"
    f1.write_text("content   ")
    f2 = root / "f2.txt"
    f2.write_text("too big content")

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(root)], 'recursive': True}
    config['filters']['max_total_tokens'] = 1000
    config['filters']['max_size_bytes'] = 5
    config['output']['max_size_placeholder'] = "Too big: {{FILENAME}}"
    config['processing']['apply_in_place'] = True
    config['processing']['compact_whitespace'] = True

    stats = find_and_combine_files(
        config,
        output_path=str(tmp_path / "out.txt"),
    )
    assert stats['total_files'] > 0

def test_main_invalid_config_error(monkeypatch):
    with patch('utils.load_and_validate_config', return_value={'pairing': {'enabled': True}, 'output': {}}):
        monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', 'config.yml', '--clipboard'])
        with pytest.raises(SystemExit) as excinfo:
            main()
    assert excinfo.value.code == 1

def test_init_copy_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    template_dir = tmp_path / "sourcecombine_dir"
    template_dir.mkdir()
    template_path = template_dir / "config.template.yml"
    template_path.write_text("template", encoding="utf-8")

    monkeypatch.setattr(sys, 'argv', ['sourcecombine.py', '--init'])

    with patch('sourcecombine.__file__', str(template_dir / "sourcecombine.py")):
        with patch('shutil.copy2', side_effect=OSError("Copy failed")):
            with pytest.raises(SystemExit) as excinfo:
                main()

    assert excinfo.value.code == 1

def test_validate_config_missing_required_keys():
    config = {"key1": "val1"}
    required_keys = ["key1", "key2"]
    with pytest.raises(InvalidConfigError, match="Config is missing required keys: key2"):
        validate_config(config, required_keys=required_keys)

def test_validate_config_output_not_dict():
    config = {"output": "not_a_dict", "search": {"root_folders": ["."]}}
    validate_config(config)

def test_validate_config_search_not_dict():
    config = {"pairing": {"enabled": True}, "search": None}
    validate_config(config)
    assert isinstance(config["search"], dict)

def test_validate_pairing_section_search_not_dict():
    config = {"pairing": {"enabled": True}, "search": None}
    _validate_pairing_section(config)
    assert isinstance(config["search"], dict)

def test_validate_output_table_of_contents_not_bool():
    config = {
        "output": {"table_of_contents": "not_a_bool"},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="'output.table_of_contents' must be true or false"):
        validate_config(config)

def test_validate_config_deprecated_in_place_groups():
    config = {
        "processing": {"in_place_groups": ["something"]},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="'processing.in_place_groups' is no longer used"):
        validate_config(config)

def test_validate_filters_max_total_tokens_invalid():
    config = {
        "filters": {"max_total_tokens": -1},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="filters.max_total_tokens must be 0 or more"):
        validate_config(config)

def test_validate_filters_search_not_dict():
    config = {
        "filters": {"inclusion_groups": {"test": {"filenames": ["*.py"]}}},
        "search": None
    }
    validate_config(config)
    assert isinstance(config["search"], dict)

def test_load_yaml_config_empty(tmp_path):
    empty_file = tmp_path / "empty.yml"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(InvalidConfigError, match="Configuration file is empty or invalid"):
        load_yaml_config(empty_file)

def test_compact_whitespace_group_none():
    text = "    "
    result = compact_whitespace(text, groups={"spaces_to_tabs": None, "trim_trailing_whitespace": False})
    assert result == "\t"

def test_validate_pairing_section_conflict():
    config = {
        "pairing": {"enabled": True},
        "search": {"root_folders": ["."], "allowed_extensions": [".txt"]}
    }
    with pytest.raises(InvalidConfigError, match="'allowed_extensions' cannot be used when pairing is enabled"):
        validate_config(config)

def test_update_file_stats_oserror():
    stats = {
        'total_files': 0,
        'total_size_bytes': 0,
        'files_by_extension': {}
    }
    file_path = MagicMock(spec=Path)
    file_path.stat.side_effect = OSError("Permission denied")
    file_path.suffix = ".txt"

    _update_file_stats(stats, file_path)

    assert stats['total_files'] == 1
    assert stats['total_size_bytes'] == 0
    assert stats['files_by_extension'][".txt"] == 1

def test_group_paths_by_stem_suffix_not_relative():
    root_path = Path("/app/project")
    file_path = Path("/other/outside.txt")

    grouped = _group_paths_by_stem_suffix([file_path], root_path=root_path)

    expected_stem = Path("/other/outside")
    assert expected_stem in grouped
    assert grouped[expected_stem][".txt"] == [file_path]

def test_token_limit_with_global_header(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    (root / "file1.txt").write_text("1234", encoding="utf-8")

    from utils import tiktoken
    monkeypatch.setattr("utils.tiktoken", None)
    monkeypatch.chdir(tmp_path)

    out_file = tmp_path / "out.txt"
    config = {
        "search": {"root_folders": [str(root)]},
        "filters": {"max_total_tokens": 1},
        "output": {
            "file": str(out_file),
            "global_header_template": "abcd",
            "format": "text"
        }
    }

    stats = find_and_combine_files(
        config,
        output_path=str(out_file)
    )

    assert stats['token_limit_reached'] is True




def test_token_approximation_fallback_coverage(tmp_path, monkeypatch):
    """Verify that token_count_is_approx is set across various features when tiktoken is missing."""
    import utils
    import sourcecombine

    # Force fallback mode
    monkeypatch.setattr(utils, "tiktoken", None)

    root = tmp_path / "root"
    root.mkdir()

    # 1. Pairing mode coverage (hits 548, 567)
    src_normal = root / "normal.c"
    src_normal.write_text("int main() { return 0; }")
    src_big = root / "big.c"
    src_big.write_text("very big content" * 100)

    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {}
    config['pairing']['enabled'] = True
    config['filters']['max_size_bytes'] = 10
    config['output']['max_size_placeholder'] = "Too big: {{FILENAME}}"

    processor = FileProcessor(config, config['output'], dry_run=False)
    paired_paths = {
        "normal": [src_normal],
        "big": [src_big]
    }
    stats = {'total_tokens': 0, 'token_count_is_approx': False, 'top_files': []}

    sourcecombine._process_paired_files(
        paired_paths,
        template="{{STEM}}.combined",
        source_exts=[".c"],
        header_exts=[".h"],
        root_path=root,
        out_folder=tmp_path / "out",
        processor=processor,
        processing_bar=None,
        dry_run=False,
        stats=stats,
        size_excluded=[src_big]
    )
    assert stats['token_count_is_approx'] is True

    # 2. Tree view coverage (hits 1095)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(root)]}

    out_file = tmp_path / "out2.txt"
    # To hit 1095, we need tree_view=True AND estimate_tokens=True
    # This path is in find_and_combine_files when list_files=True OR tree_view=True
    stats = find_and_combine_files(
        config,
        output_path=str(out_file),
        estimate_tokens=True,
        tree_view=True
    )
    assert stats['token_count_is_approx'] is True

    # 3. Include Tree and TOC coverage (hits 1264, 1281)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config['search'] = {'root_folders': [str(root)]}
    config['output']['table_of_contents'] = True
    config['output']['include_tree'] = True

    out_file = tmp_path / "out3.txt"
    # To hit 1264 and 1281, we need tree_view=False AND estimate_tokens=True
    stats = find_and_combine_files(
        config,
        output_path=str(out_file),
        estimate_tokens=True,
        tree_view=False
    )
    assert stats['token_count_is_approx'] is True
