import pytest
from pathlib import Path
from utils import get_project_identity

def test_get_project_identity_pubspec(tmp_path):
    """Test that pubspec.yaml is correctly parsed for project identity."""
    pubspec_content = "name: my_flutter_app\ndescription: A new Flutter project.\nversion: 1.2.3+4\n"
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content, encoding='utf-8')

    identity = get_project_identity(tmp_path)

    assert identity["project_name"] == "my_flutter_app"
    assert identity["project_version"] == "1.2.3+4"
    assert identity["project_description"] == "A new Flutter project."
    assert identity["manifest_source"] == "pubspec.yaml"

def test_get_project_identity_pubspec_quotes(tmp_path):
    """Test that pubspec.yaml with quotes is correctly parsed."""
    pubspec_content = "name: \"quoted_app\"\ndescription: 'Single quoted description'\nversion: \"2.0.0\"\n"
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content, encoding='utf-8')

    identity = get_project_identity(tmp_path)

    assert identity["project_name"] == "quoted_app"
    assert identity["project_version"] == "2.0.0"
    assert identity["project_description"] == "Single quoted description"
    assert identity["manifest_source"] == "pubspec.yaml"

def test_get_project_identity_pubspec_partial(tmp_path):
    """Test that pubspec.yaml with missing fields is handled."""
    pubspec_content = "name: partial_app\n"
    pubspec_file = tmp_path / "pubspec.yaml"
    pubspec_file.write_text(pubspec_content, encoding='utf-8')

    identity = get_project_identity(tmp_path)

    assert identity["project_name"] == "partial_app"
    assert identity["project_version"] == ""
    assert identity["project_description"] == ""
    assert identity["manifest_source"] == "pubspec.yaml"
