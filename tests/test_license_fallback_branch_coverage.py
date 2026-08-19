import json
from pathlib import Path
from utils import get_project_identity, _parse_json_manifest


def test_license_fallback_when_license_populated_and_author_missing(tmp_path: Path):
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps({
        "name": "my-pkg",
        "version": "1.0.0",
        "license": "MIT"
    }), encoding="utf-8")

    license_file = tmp_path / "LICENSE"
    license_file.write_text(
        "The MIT License\n\nCopyright (c) 2025 Jane Doe\n\nAll rights reserved.",
        encoding="utf-8"
    )

    identity = get_project_identity(tmp_path)
    assert identity["project_license"] == "MIT"
    assert identity["project_author"] == "Jane Doe"


def test_license_fallback_when_author_populated_and_license_missing(tmp_path: Path):
    package_json = tmp_path / "package.json"
    package_json.write_text(json.dumps({
        "name": "my-pkg",
        "version": "1.0.0",
        "author": "John Smith"
    }), encoding="utf-8")

    license_file = tmp_path / "LICENSE"
    license_file.write_text(
        "Apache License Version 2.0\n\nCopyright 2025 John Smith",
        encoding="utf-8"
    )

    identity = get_project_identity(tmp_path)
    assert identity["project_author"] == "John Smith"
    assert identity["project_license"] == "Apache"


def test_parse_json_manifest_repository_dict_without_url():
    identity = {}
    manifest_data = {
        "name": "test-repo",
        "repository": {"type": "git"}
    }
    class MockPath:
        def is_file(self):
            return True
        def read_text(self, encoding="utf-8"):
            return json.dumps(manifest_data)

    result = _parse_json_manifest(MockPath(), identity)
    assert result is True
    assert "project_url" not in identity


def test_sln_referencing_non_existent_csproj(tmp_path: Path):
    sln_file = tmp_path / "App.sln"
    sln_file.write_text(
        'Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "NonExistent", "NonExistent.csproj", "{12345678}"',
        encoding="utf-8"
    )

    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name
    assert identity["manifest_source"] == "App.sln"
