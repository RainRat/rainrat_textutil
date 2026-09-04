import re
import utils


def test_get_project_identity_pyproject_direct_license(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "direct_lic_pkg"\nversion = "1.0.0"\nlicense = "MIT"\n',
        encoding="utf-8",
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "direct_lic_pkg"
    assert identity["project_license"] == "MIT"


def test_get_project_identity_readme_blank_lines(tmp_path):
    (tmp_path / "README.md").write_text(
        "# My Project Title\n\n\n\nThis is the description paragraph.\n",
        encoding="utf-8",
    )
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "My Project Title"
    assert identity["project_description"] == "This is the description paragraph."


def test_get_project_identity_cargo_existing_url_no_homepage(tmp_path, monkeypatch):
    csproj = tmp_path / "app.csproj"
    csproj.write_text(
        "<Project><PropertyGroup><PackageProjectUrl>https://existing.url</PackageProjectUrl></PropertyGroup></Project>",
        encoding="utf-8",
    )

    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        '[package]\nname = "cargo_pkg"\nversion = "0.1.0"\nrepository = "https://repo.url"\n',
        encoding="utf-8",
    )

    original_search = re.search

    def mock_search(pattern, string, *args, **kwargs):
        res = original_search(pattern, string, *args, **kwargs)
        if pattern == r'<PackageLicenseExpression>(.*?)</PackageLicenseExpression>' and "existing.url" in string:
            raise RuntimeError("Fail after setting project_url")
        return res

    monkeypatch.setattr(re, "search", mock_search)

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "cargo_pkg"
    assert identity["manifest_source"] == "Cargo.toml"


def test_get_project_identity_pubspec_existing_url_no_homepage(tmp_path, monkeypatch):
    csproj = tmp_path / "app.csproj"
    csproj.write_text(
        "<Project><PropertyGroup><PackageProjectUrl>https://existing.url</PackageProjectUrl></PropertyGroup></Project>",
        encoding="utf-8",
    )

    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text(
        "name: pub_pkg\nversion: 1.0.0\nrepository: https://repo.url\n",
        encoding="utf-8",
    )

    original_search = re.search

    def mock_search(pattern, string, *args, **kwargs):
        res = original_search(pattern, string, *args, **kwargs)
        if pattern == r'<PackageLicenseExpression>(.*?)</PackageLicenseExpression>' and "existing.url" in string:
            raise RuntimeError("Fail after setting project_url")
        return res

    monkeypatch.setattr(re, "search", mock_search)

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "pub_pkg"
    assert identity["manifest_source"] == "pubspec.yaml"


def test_get_project_identity_empty_license_file_skipped(tmp_path):
    (tmp_path / "LICENSE").write_text("", encoding="utf-8")
    (tmp_path / "LICENSE.txt").write_text(
        "MIT License\nCopyright (c) 2024 Jane Doe", encoding="utf-8"
    )

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_license"] == "MIT"
    assert identity["project_author"] == "Jane Doe"


def test_get_project_identity_author_preset_license_extracted(tmp_path):
    (tmp_path / "pubspec.yaml").write_text(
        "name: flutter_app\nauthor: John Doe\n", encoding="utf-8"
    )
    (tmp_path / "LICENSE").write_text(
        "Apache License 2.0\nCopyright (c) 2024 Other Author", encoding="utf-8"
    )

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "flutter_app"
    assert identity["project_author"] == "John Doe"
    assert identity["project_license"] == "Apache"
