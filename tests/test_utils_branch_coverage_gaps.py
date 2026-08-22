import tempfile
from pathlib import Path
from utils import get_project_identity


def test_gradle_settings_without_rootproject_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "settings.gradle").write_text("// gradle settings file without rootProject.name", encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "settings.gradle"
        assert identity["project_name"] == tmp_path.name
        assert identity["project_version"] == ""


def test_gradle_build_without_version():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "settings.gradle").write_text("rootProject.name = 'my-gradle-app'", encoding="utf-8")
        (tmp_path / "build.gradle").write_text("// no version specified", encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "settings.gradle"
        assert identity["project_name"] == "my-gradle-app"
        assert identity["project_version"] == ""


def test_clojure_project_clj_without_defproject():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "project.clj").write_text("; commentary without defproject", encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "project.clj"
        assert identity["project_name"] == tmp_path.name


def test_podspec_without_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "my.podspec").write_text("# podspec without name", encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "my.podspec"
        assert identity["project_name"] == tmp_path.name


def test_pyproject_toml_author_dict_without_name_and_urls():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        content = (
            "[project]\n"
            'name = "py-app"\n'
            'authors = [{ email = "dev@example.com" }]\n'
            'urls = { homepage = "https://example.com" }\n'
        )
        (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "pyproject.toml"
        assert identity["project_name"] == "py-app"
        assert identity["project_author"] == ""
        assert identity["project_url"] == "https://example.com"


def test_cargo_toml_without_package_section_and_with_homepage():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        content = (
            "[package]\n"
            'name = "rust-app"\n'
            'homepage = "https://rust-app.org"\n'
        )
        (tmp_path / "Cargo.toml").write_text(content, encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "Cargo.toml"
        assert identity["project_name"] == "rust-app"
        assert identity["project_url"] == "https://rust-app.org"


def test_cargo_toml_workspace_only():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "Cargo.toml").write_text("[workspace]\nmembers = []\n", encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "Cargo.toml"
        assert identity["project_name"] == tmp_path.name


def test_mix_exs_without_app_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "mix.exs").write_text("# mix config without app:", encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "mix.exs"
        assert identity["project_name"] == tmp_path.name


def test_julia_project_toml_without_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "Project.toml").write_text('uuid = "12345"', encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "Project.toml"
        assert identity["project_name"] == tmp_path.name


def test_zig_build_zon_without_name():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "build.zig.zon").write_text('.version = "1.0.0"', encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "build.zig.zon"
        assert identity["project_name"] == tmp_path.name


def test_pubspec_yaml_without_name_and_with_homepage():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        content = (
            'homepage: https://flutter-app.dev\n'
            'environment:\n'
            '  sdk: ">=2.12.0"\n'
        )
        (tmp_path / "pubspec.yaml").write_text(content, encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["manifest_source"] == "pubspec.yaml"
        assert identity["project_name"] == tmp_path.name
        assert identity["project_url"] == "https://flutter-app.dev"


def test_readme_with_subheaders_and_underlines_only():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        content = "# Main Header\n## Subheader\n===\n---"
        (tmp_path / "README.md").write_text(content, encoding="utf-8")
        identity = get_project_identity(tmp_path)
        assert identity["project_name"] == "Main Header"
        assert identity["project_description"] == ""
