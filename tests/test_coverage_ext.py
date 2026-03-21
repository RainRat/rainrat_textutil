import pytest
import utils
import sourcecombine
from unittest.mock import patch
import copy

def test_apply_in_place_full_pass(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\n\n\nline2", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['processing'] = {
        'apply_in_place': True,
        'create_backups': True,
        'compact_whitespace': True,
        'compact_whitespace_groups': {'compact_blank_lines': True}
    }
    config['search']['root_folders'] = [str(tmp_path)]
    config['filters']['max_total_lines'] = 100

    sourcecombine.find_and_combine_files(
        config,
        output_path=str(tmp_path / "combined.txt")
    )

    updated_content = test_file.read_text(encoding="utf-8")
    assert "line1\n\nline2" in updated_content
    assert "\n\n\n" not in updated_content

def test_token_count_is_approx_paired(tmp_path):
    root = tmp_path / "project"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    source_path = src_dir / "example.cpp"
    source_path.write_text("some content", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    processor = sourcecombine.FileProcessor(config, config["output"], dry_run=False)

    pairs = [("example", [source_path])]
    out_folder = root / "out"
    stats = {
        'total_tokens': 0,
        'total_lines': 0,
        'token_count_is_approx': False,
        'top_files': [],
        'files_by_extension': {}
    }

    with patch("utils.tiktoken", None):
        sourcecombine._process_paired_files(
            pairs,
            template="{{STEM}}.out",
            source_exts=(".cpp",),
            header_exts=(),
            root_path=root,
            out_folder=out_folder,
            processor=processor,
            processing_bar=None,
            stats=stats,
            dry_run=False,
        )

    assert stats['token_count_is_approx'] is True

def test_token_count_is_approx_paired_with_placeholder(tmp_path):
    root = tmp_path / "project"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    source_path = src_dir / "example.cpp"
    source_path.write_text("some content", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['output']['max_size_placeholder'] = "File {{FILENAME}} too big"
    processor = sourcecombine.FileProcessor(config, config["output"], dry_run=False)

    pairs = [("example", [source_path])]
    out_folder = root / "out"
    stats = {
        'total_tokens': 0,
        'total_lines': 0,
        'token_count_is_approx': False,
        'top_files': [],
        'files_by_extension': {}
    }

    size_excluded = [source_path]

    with patch("utils.tiktoken", None):
        sourcecombine._process_paired_files(
            pairs,
            template="{{STEM}}.out",
            source_exts=(".cpp",),
            header_exts=(),
            root_path=root,
            out_folder=out_folder,
            processor=processor,
            processing_bar=None,
            stats=stats,
            dry_run=False,
            size_excluded=size_excluded
        )

    assert stats['token_count_is_approx'] is True

def test_token_count_is_approx_find_and_combine(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("some content", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config['search']['root_folders'] = [str(tmp_path)]
    config['output']['include_tree'] = True
    config['output']['table_of_contents'] = True
    config['filters']['max_total_lines'] = 100

    with patch("utils.tiktoken", None):
        stats = sourcecombine.find_and_combine_files(
            config,
            output_path=str(tmp_path / "combined.txt")
        )

    assert stats['token_count_is_approx'] is True

    config['filters']['max_total_lines'] = 0
    config['filters']['max_total_tokens'] = 0
    config['output']['sort_by'] = 'name'

    with patch("utils.tiktoken", None):
        stats = sourcecombine.find_and_combine_files(
            config,
            output_path=str(tmp_path / "combined2.txt")
        )
    assert stats['token_count_is_approx'] is True

def test_paired_global_templates(tmp_path):
    root = tmp_path / "project"
    src_dir = root / "src"
    src_dir.mkdir(parents=True)
    source_path = src_dir / "example.cpp"
    source_path.write_text("content", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    processor = sourcecombine.FileProcessor(config, config["output"], dry_run=False)

    pairs = [("example", [source_path])]
    out_folder = root / "out"

    sourcecombine._process_paired_files(
        pairs,
        template="{{STEM}}.out",
        source_exts=(".cpp",),
        header_exts=(),
        root_path=root,
        out_folder=out_folder,
        processor=processor,
        processing_bar=None,
        global_header="GLOBAL START",
        global_footer="GLOBAL END",
        dry_run=False,
    )

    output_file = out_folder / "example.out"
    content = output_file.read_text(encoding="utf-8")
    assert content.startswith("GLOBAL START")
    assert content.endswith("GLOBAL END")

def test_main_invalid_config_verbose(tmp_path, caplog):
    invalid_config = tmp_path / "invalid.yml"
    invalid_config.write_text("search: not_a_dict", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine.py", str(invalid_config), "-v"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 1

    assert "The configuration is not valid" in caplog.text

def test_main_search_validation_error_verbose(tmp_path, caplog):
    config_file = tmp_path / "config.yml"
    config_file.write_text("search:\n  max_depth: -1", encoding="utf-8")

    with patch("sys.argv", ["sourcecombine.py", str(config_file), "-v"]):
        with pytest.raises(SystemExit) as exc:
            sourcecombine.main()
        assert exc.value.code == 1
    assert "The configuration is not valid" in caplog.text

def test_main_init_os_error(tmp_path, caplog):
    with patch("sys.argv", ["sourcecombine.py", "--init"]):
        with patch("shutil.copy2", side_effect=OSError("Permission denied")):
            with pytest.raises(SystemExit) as exc:
                sourcecombine.main()
            assert exc.value.code == 1
    assert "Could not copy the template file" in caplog.text
