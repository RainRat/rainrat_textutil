import tempfile
from pathlib import Path
from utils import get_project_identity


def test_readme_no_headers():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        readme = tmp_path / "README.md"
        readme.write_text("This is just plain text without any markdown headers.\nLine two.", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] is None
        assert identity["project_name"] == tmp_path.name


def test_readme_header_at_end_empty_remaining():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        readme = tmp_path / "README.md"
        readme.write_text("# My Project Header\n   \n", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == "My Project Header"
        assert identity["project_description"] == ""


def test_readme_subsequent_header_ignored_as_description():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        readme = tmp_path / "README.md"
        readme.write_text("# My Project\n\n## Subheader Here\n\nSome text.", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == "My Project"
        assert identity["project_description"] == ""


def test_readme_description_truncated_over_200_chars():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        readme = tmp_path / "README.md"
        long_desc = "A" * 250
        readme.write_text(f"# Title\n\n{long_desc}", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["project_description"] == ("A" * 197) + "..."


def test_license_author_and_license_already_set_skips_license_fallback():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        pkg = tmp_path / "package.json"
        pkg.write_text('{"name": "test-pkg", "author": "Alice", "license": "MIT"}', encoding="utf-8")
        license_file = tmp_path / "LICENSE"
        license_file.write_text("Copyright 2024 Bob\nSome License", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["project_author"] == "Alice"
        assert identity["project_license"] == "MIT"


def test_license_file_empty_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        license_file = tmp_path / "LICENSE"
        license_file.write_text("   \n", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["project_license"] == ""


def test_license_copyright_author_empty_after_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        license_file = tmp_path / "LICENSE"
        license_file.write_text("Custom License Text\nCopyright 2024 . All rights reserved.", encoding="utf-8")

        identity = get_project_identity(tmp_path)
        assert identity["project_license"] == "Custom License Text"
        assert identity["project_author"] == ""
