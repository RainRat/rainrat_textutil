import json
from pathlib import Path
import utils

def test_get_project_identity_php(tmp_path):
    composer_json = tmp_path / "composer.json"
    composer_json.write_text(json.dumps({
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
    pom_xml = tmp_path / "pom.xml"
    pom_xml.write_text("""
<project>
    <artifactId>java-project</artifactId>
    <version>2.0.0</version>
    <description>A Java project</description>
    <licenses>
        <license>
            <name>Apache-2.0</name>
        </license>
    </licenses>
</project>
""", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "java-project"
    assert identity["project_version"] == "2.0.0"
    assert identity["project_description"] == "A Java project"
    assert identity["project_license"] == "Apache-2.0"

def test_get_project_identity_go(tmp_path):
    go_mod = tmp_path / "go.mod"
    go_mod.write_text("module github.com/user/go-project", encoding='utf-8')
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "github.com/user/go-project"

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
