import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import argparse
import copy
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import utils
from sourcecombine import (
    ColoredArgumentParser,
    _generate_table_of_contents,
    _print_execution_summary,
    collect_git_diff_files,
    collect_git_files,
    filter_file_paths,
    find_and_combine_files,
)


def test_cargo_toml_repository_fallback_when_project_url_preset():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        podspec = tmp / "foo.podspec"
        podspec.write_text('.homepage = "https://podspec-preset.com"\n')

        cargo = tmp / "Cargo.toml"
        cargo.write_text('[package]\nname = "mycargo"\nrepository = "https://github.com/rust/repo"\n')

        with patch.object(Path, "name", new_callable=PropertyMock) as mock_name:
            def side_effect():
                if mock_name.call_count == 1:
                    return "foo.podspec"
                raise ValueError("podspec parse break")

            mock_name.side_effect = side_effect
            ident = utils.get_project_identity(tmp)
            assert ident["project_name"] == "mycargo"
            assert ident["project_url"] == "https://podspec-preset.com"
            assert ident["manifest_source"] == "Cargo.toml"


def test_pubspec_yaml_repository_fallback_when_project_url_preset():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        podspec = tmp / "foo.podspec"
        podspec.write_text('.homepage = "https://podspec-preset.com"\n')

        pubspec = tmp / "pubspec.yaml"
        pubspec.write_text("name: mypub\nrepository: https://github.com/dart/repo\n")

        with patch.object(Path, "name", new_callable=PropertyMock) as mock_name:
            def side_effect():
                if mock_name.call_count == 1:
                    return "foo.podspec"
                raise ValueError("podspec parse break")

            mock_name.side_effect = side_effect
            ident = utils.get_project_identity(tmp)
            assert ident["project_name"] == "mypub"
            assert ident["project_url"] == "https://podspec-preset.com"
            assert ident["manifest_source"] == "pubspec.yaml"


def test_readme_parsing_with_empty_lines_and_subheaders():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        readme = tmp / "README.md"
        readme.write_text("# My Project Title\n\n## Table of Contents\n---\n===\n")

        ident = utils.get_project_identity(tmp)
        assert ident["project_name"] == "My Project Title"
        assert ident["project_description"] == ""


def test_collect_git_files_with_empty_stdout_lines():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="file1.txt\n\nfile2.txt\n")
        paths, cwd, count = collect_git_files(".", progress=MagicMock())
        assert len(paths) == 2


def test_collect_git_diff_files_with_empty_stdout_lines():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        f1 = tmp / "file1.txt"
        f1.write_text("content")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="file1.txt\n\n")
            paths, cwd, count = collect_git_diff_files(tmp, staged_only=True)
            assert len(paths) == 1


def test_filter_file_paths_when_reason_is_none():
    with patch("sourcecombine.should_include", return_value=(False, None)):
        reasons = {}
        filtered = filter_file_paths(
            [Path("test.txt")],
            filter_opts={},
            search_opts={},
            root_path=Path("."),
            stats={"filter_reasons": reasons},
        )
        assert len(filtered) == 0
        assert len(reasons) == 0


def test_generate_table_of_contents_when_path_not_in_information():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        p = tmp / "file.txt"
        p.write_text("content")
        toc = _generate_table_of_contents(
            [(p, tmp)], output_format="markdown", information={"other.txt": {"lines": 10}}
        )
        assert "[file.txt](#filetxt)" in toc


def test_find_and_combine_files_with_custom_header_footer_in_mirror_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "file.py"
        p.write_text("print(123)")
        out_file = Path(tmpdir) / "out.txt"

        cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
        cfg["search"]["root_folder"] = tmpdir
        cfg["pairing"]["enabled"] = False
        cfg["output"]["mirror"] = True
        cfg["output"]["header_template"] = "CUSTOM HEADER"
        cfg["output"]["footer_template"] = "CUSTOM FOOTER"

        find_and_combine_files(cfg, str(out_file), dry_run=True, explicit_files=[p])
        assert cfg["output"]["header_template"] == "CUSTOM HEADER"
        assert cfg["output"]["footer_template"] == "CUSTOM FOOTER"


def test_find_and_combine_files_max_files_higher_than_paired_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "main.c").write_text("c")
        (Path(tmpdir) / "main.h").write_text("h")
        out_file = Path(tmpdir) / "out.txt"
        cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
        cfg["search"]["root_folder"] = tmpdir
        cfg["pairing"]["enabled"] = True
        cfg["filters"]["max_files"] = 100
        output = find_and_combine_files(cfg, str(out_file), dry_run=True)
        assert output is not None


def test_find_and_combine_files_json_format_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "main.c"
        p.write_text("c")
        out_file = Path(tmpdir) / "out.json"
        cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
        cfg["search"]["root_folder"] = tmpdir
        cfg["pairing"]["enabled"] = False
        output = find_and_combine_files(
            cfg, str(out_file), dry_run=True, output_format="json", explicit_files=[p]
        )
        assert output is not None


def test_find_and_combine_files_empty_max_size_placeholder():
    with tempfile.TemporaryDirectory() as tmpdir:
        p = Path(tmpdir) / "large.txt"
        p.write_text("x" * 100)
        out_file = Path(tmpdir) / "out.txt"
        cfg = copy.deepcopy(utils.DEFAULT_CONFIG)
        cfg["search"]["root_folder"] = tmpdir
        cfg["pairing"]["enabled"] = False
        cfg["filters"]["max_file_size"] = 10
        cfg["output"]["max_size_placeholder"] = ""
        output = find_and_combine_files(cfg, str(out_file), dry_run=True, explicit_files=[p])
        assert output is not None


def test_colored_argument_parser_error_variations():
    parser = ColoredArgumentParser(prog="test")
    parser.add_argument("--format", choices=["text", "json"])

    try:
        parser.error("unrecognized arguments bad_arg")
    except SystemExit:
        pass

    try:
        parser.error("invalid choice: foo")
    except SystemExit:
        pass

    try:
        parser.error("argument --format: invalid choice: bar (choose from text, json)")
    except SystemExit:
        pass


def test_print_execution_summary_with_tokens_as_primary_metric():
    stats = {
        "combined_file_count": 1,
        "combined_line_count": 10,
        "combined_token_count": 5,
        "total_bytes": 100,
        "processing_time": 0.1,
        "limit_reached": False,
        "filter_reasons": {},
        "metric_distributions": {
            "lines": {"total": 10, "min": 10, "max": 10, "avg": 10, "min_file": "a", "max_file": "a"},
            "tokens": {"total": 5, "min": 5, "max": 5, "avg": 5, "min_file": "a", "max_file": "a"},
            "size": {"total": 100, "min": 100, "max": 100, "avg": 100, "min_file": "a", "max_file": "a"},
        },
        "file_details": [{"path": "a", "lines": 10, "tokens": 5, "size": 100, "lang": "txt"}],
    }
    args = argparse.Namespace(
        sort="tokens",
        format="text",
        json_summary=None,
        list_files=False,
        quiet=False,
        verbose=False,
        dry_run=False,
    )
    _print_execution_summary(stats, args, pairing_enabled=False)
