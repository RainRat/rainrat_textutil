import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import utils

def test_save_yaml_config_oserror():
    """Cover lines 259-260: OSError during yaml save."""
    with patch("builtins.open", mock_open()) as mocked_file:
        mocked_file.side_effect = OSError("Mocked error")
        with pytest.raises(utils.InvalidConfigError, match="Could not write configuration file: Mocked error"):
            utils.save_yaml_config("dummy.yml", {"key": "value"})

def test_get_project_identity_php(tmp_path):
    """Cover lines 1450-1463: composer.json parsing."""
    composer = tmp_path / "composer.json"
    composer.write_text(json.dumps({
        "name": "php-project",
        "version": "1.0.0",
        "description": "A PHP project",
        "license": "MIT"
    }), encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "php-project"
    assert identity["project_version"] == "1.0.0"
    assert identity["project_description"] == "A PHP project"
    assert identity["project_license"] == "MIT"

def test_get_project_identity_java(tmp_path):
    """Cover lines 1468-1486: pom.xml parsing."""
    pom = tmp_path / "pom.xml"
    pom.write_text("""
<project>
    <artifactId>java-app</artifactId>
    <version>2.1.0</version>
    <description>A Java application</description>
    <licenses>
        <license>
            <name>Apache-2.0</name>
        </license>
    </licenses>
</project>
""", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "java-app"
    assert identity["project_version"] == "2.1.0"
    assert identity["project_description"] == "A Java application"
    assert identity["project_license"] == "Apache-2.0"

def test_get_project_identity_go(tmp_path):
    """Cover lines 1491-1498: go.mod parsing."""
    gomod = tmp_path / "go.mod"
    gomod.write_text("module github.com/user/go-project\n", encoding='utf-8')

    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "github.com/user/go-project"

def test_get_project_identity_cargo_exception(tmp_path):
    """Cover lines 1444-1445: Exception during Cargo.toml processing."""
    cargo = tmp_path / "Cargo.toml"
    cargo.touch()

    # We want to trigger the 'except Exception' at line 1444.
    # It happens inside the 'if cargo.is_file():' block when reading or processing.
    with patch.object(Path, "read_text", side_effect=Exception("Read error")):
        identity = utils.get_project_identity(tmp_path)
        # Should fall through to next check (PHP) or return default identity
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_php_exception(tmp_path):
    """Cover lines 1462-1463: Exception during composer.json processing."""
    composer = tmp_path / "composer.json"
    composer.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Read error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_java_exception(tmp_path):
    """Cover lines 1485-1486: Exception during pom.xml processing."""
    pom = tmp_path / "pom.xml"
    pom.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Read error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_go_exception(tmp_path):
    """Cover lines 1497-1498: Exception during go.mod processing."""
    gomod = tmp_path / "go.mod"
    gomod.touch()
    with patch.object(Path, "read_text", side_effect=Exception("Read error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_outer_exception(tmp_path):
    """Cover lines 1500-1501: Outer Exception in get_project_identity."""
    # Triggering outer exception by mocking Path.is_file to raise exception on first call
    with patch.object(Path, "is_file", side_effect=Exception("Outer error")):
        identity = utils.get_project_identity(tmp_path)
        assert identity["project_name"] == tmp_path.name

def test_get_project_identity_composer_invalid_json(tmp_path):
    composer_json = tmp_path / "composer.json"
    composer_json.write_text("invalid json", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    # Should fall back to directory name or default
    assert identity["project_name"] == tmp_path.name

def test_get_project_identity_pom_invalid_xml(tmp_path):
    pom_xml = tmp_path / "pom.xml"
    pom_xml.write_text("invalid xml", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

def test_get_project_identity_go_mod_no_module(tmp_path):
    go_mod = tmp_path / "go.mod"
    go_mod.write_text("not a module line", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == tmp_path.name

