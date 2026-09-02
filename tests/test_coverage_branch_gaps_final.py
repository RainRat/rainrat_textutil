import io
import argparse
from pathlib import Path
from utils import get_project_identity
from sourcecombine import (
    _render_template,
    _resolve_information_placeholders,
    FileProcessor,
    _print_execution_summary,
)


def test_get_project_identity_pyproject_table_license(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\nversion = "1.0"\nlicense = { text = "MIT" }\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "demo"
    assert identity["project_license"] == "MIT"


def test_get_project_identity_pyproject_section_license(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "demo"\nversion = "1.0"\n\n[project.license]\ntext = "Apache-2.0"\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "demo"
    assert identity["project_license"] == "Apache-2.0"


def test_get_project_identity_cargo_repository_no_homepage(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        '[package]\nname = "mycrate"\nversion = "0.1.0"\nrepository = "https://repo.com"\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "mycrate"
    assert identity["project_url"] == "https://repo.com"


def test_get_project_identity_cargo_homepage_and_repository(tmp_path):
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        '[package]\nname = "mycrate"\nversion = "0.1.0"\nhomepage = "https://example.com"\nrepository = "https://repo.com"\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "mycrate"
    assert identity["project_url"] == "https://example.com"


def test_get_project_identity_pubspec_repository_no_homepage(tmp_path):
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text(
        "name: myflutter\nversion: 1.0.0\nrepository: https://repo.com\n",
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "myflutter"
    assert identity["project_url"] == "https://repo.com"


def test_get_project_identity_readme_subheader_following(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project Name\n\n## Subheader 1\n", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Project Name"
    assert identity["project_description"] == ""


def test_get_project_identity_readme_description_text_following(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project Name\n\nCool description text.\n", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Project Name"
    assert identity["project_description"] == "Cool description text."


def test_get_project_identity_readme_no_remaining_lines(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project Name", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Project Name"
    assert identity["project_description"] == ""


def test_resolve_information_placeholders_existing_project_url():
    template = "URL: {{PROJECT_URL}}"
    data = {"project_url": "https://data.url"}
    replacements = {"{{PROJECT_URL}}": "https://override.url"}
    _resolve_information_placeholders(template, replacements, data)
    assert replacements["{{PROJECT_URL}}"] == "https://override.url"


def test_render_template_file_url_missing_remote_url():
    template = "File: {{FILE_URL}}"
    git_info = {"git_remote_url": None, "git_commit": "123456", "git_repo_root": "/repo"}
    result = _render_template(template, Path("file.py"), git_info=git_info)
    assert "File: " in result


def test_file_processor_collapsible_markdown_zero_counts(tmp_path):
    processor = FileProcessor(
        config={},
        output_opts={"collapsible": True},
        output_format="markdown",
    )
    outfile = io.StringIO()
    processor._write_with_templates(
        outfile=outfile,
        file_path=tmp_path / "test.txt",
        relative_path=Path("test.txt"),
        content="hello",
        lines=0,
        size=None,
        tokens=0,
    )
    output = outfile.getvalue()
    assert "<details><summary><b>test.txt</b></summary>" in output


def test_file_processor_json_without_modified(tmp_path):
    processor = FileProcessor(
        config={},
        output_opts={"skip_content": False},
        output_format="json",
    )
    outfile = io.StringIO()
    processor._write_with_templates(
        outfile=outfile,
        file_path=tmp_path / "test.txt",
        relative_path=Path("test.txt"),
        content="hello world",
        lines=1,
        size=11,
        tokens=2,
        modified=None,
    )
    output = outfile.getvalue()
    assert '"modified"' not in output


def test_execution_summary_sorted_by_lines_and_size():
    stats = {
        "files_combined": 2,
        "total_files": 2,
        "total_lines": 100,
        "total_bytes": 1000,
        "total_tokens": 200,
        "is_tokens_approx": False,
        "folder_stats": {
            "src": {"tokens": 120, "lines": 60, "size": 600, "files": 1},
            "tests": {"tokens": 80, "lines": 40, "size": 400, "files": 1},
        },
        "lang_stats": {
            "Python": {"tokens": 200, "lines": 100, "size": 1000, "files": 2},
        },
    }

    for sort_metric in ["lines", "size"]:
        args = argparse.Namespace(
            quiet=False,
            json=False,
            dry_run=False,
            extract=False,
            list_files=False,
            tree=False,
            estimate_tokens=False,
            format="text",
            sort=sort_metric,
            show_folder_stats=True,
            show_lang_stats=True,
            show_largest=False,
            top_folders=5,
            top_languages=5,
            limit=None,
            line_limit=None,
            total_size_limit=None,
            max_lines=None,
            max_depth=None,
        )
        _print_execution_summary(
            stats=stats,
            args=args,
            pairing_enabled=False,
            destination_desc="stdout",
            duration=0.5,
            source_desc=".",
        )
