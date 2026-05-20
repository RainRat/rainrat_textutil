from pathlib import Path
from unittest.mock import MagicMock
from sourcecombine import (
    _resolve_metadata_placeholders,
    collect_file_paths,
    filter_file_paths,
    _pair_files
)

def test_resolve_metadata_placeholders_with_empty_template():
    replacements = {}
    _resolve_metadata_placeholders("", replacements, {})
    assert replacements == {}

def test_resolve_metadata_placeholders_preserves_existing_keys():
    replacements = {"{{GIT_BRANCH}}": "already_set"}
    data = {"git_branch": "new_branch"}
    _resolve_metadata_placeholders("{{GIT_BRANCH}}", replacements, data)
    assert replacements["{{GIT_BRANCH}}"] == "already_set"

def test_collect_file_paths_for_single_file_updates_progress(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")

    progress = MagicMock()
    paths, root, count = collect_file_paths(str(f), recursive=False, exclude_folders=[], progress=progress)

    assert paths == [f]
    progress.update.assert_called_once_with(1)

def test_filter_file_paths_handles_null_stats_dictionary(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("content")

    paths = [f]
    filter_opts = {
        'exclude_patterns': [],
        'include_patterns': [],
        'exclude_folders': [],
        'max_depth': 0,
        'skip_binary': False,
        'max_size_bytes': 1,
        'min_size_bytes': 0,
    }
    search_opts = {
        'include_grep': None,
        'exclude_grep': None,
    }

    filtered = filter_file_paths(
        paths,
        root_path=tmp_path,
        filter_opts=filter_opts,
        search_opts=search_opts,
        stats=None
    )
    assert f not in filtered

def test_pair_files_deduplicates_identical_header_and_source_paths(tmp_path):
    f = tmp_path / "main.cpp"
    f.write_text("int main() {}")

    filtered_paths = [f]
    source_exts = {".cpp"}
    header_exts = {".cpp"}

    paired = _pair_files(filtered_paths, source_exts, header_exts, include_mismatched=True, root_path=tmp_path)

    assert len(paired) == 1
    pair_key, files = paired[0]
    assert files == [f]
