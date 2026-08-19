import json
from utils import get_project_identity, _parse_json_manifest


def test_parse_json_manifest_repository_dict_without_url(tmp_path):
    manifest_path = tmp_path / "package.json"
    manifest_path.write_text(json.dumps({"repository": {"type": "git"}}), encoding="utf-8")
    identity = {}
    assert _parse_json_manifest(manifest_path, identity) is True
    assert identity.get("project_url", "") == ""


def test_dotnet_sln_matching_nonexistent_project_file(tmp_path):
    sln_file = tmp_path / "test.sln"
    sln_file.write_text(
        'Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "App", "Missing.csproj"',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["manifest_source"] == "test.sln"
    assert identity["project_name"] == tmp_path.name


def test_readme_description_header_immediately_follows_h1(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Project Title\n## Subtitle\nSome description", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Project Title"
    assert identity["project_description"] == ""


def test_readme_description_truncation_over_200_chars(tmp_path):
    long_desc = "A" * 250
    readme = tmp_path / "README.md"
    readme.write_text(f"# Project Title\n\n{long_desc}", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Project Title"
    assert len(identity["project_description"]) == 200
    assert identity["project_description"].endswith("...")


def test_license_long_first_line_fallback(tmp_path):
    long_first_line = "This is a custom header line that is much longer than fifty characters in total"
    license_file = tmp_path / "LICENSE"
    license_file.write_text(f"{long_first_line}\nCopyright (c) 2023 Developer", encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "LICENSE"
    assert identity["project_author"] == "Developer"


def test_deno_json_authors_array(tmp_path):
    deno_file = tmp_path / "deno.json"
    deno_file.write_text(
        json.dumps({"name": "deno-app", "authors": ["Alice <alice@example.com>", "Bob"]}),
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "deno-app"
    assert identity["project_author"] == "Alice <alice@example.com>, Bob"


def test_zig_zon_missing_version(tmp_path):
    zig_file = tmp_path / "build.zig.zon"
    zig_file.write_text('.name = "zig-project",', encoding="utf-8")
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "zig-project"
    assert identity["project_version"] == ""


def test_pubspec_homepage_and_repository_precedence(tmp_path):
    pubspec = tmp_path / "pubspec.yaml"
    pubspec.write_text(
        "name: flutter_app\nhomepage: https://homepage.org\nrepository: https://repo.org",
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "flutter_app"
    assert identity["project_url"] == "https://homepage.org"
