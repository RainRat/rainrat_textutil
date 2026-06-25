import json
from pathlib import Path
import utils

def test_project_identity_deno_json(tmp_path):
    """Test that project identity is correctly detected from deno.json."""
    deno_json = tmp_path / "deno.json"
    deno_json.write_text(json.dumps({
        "name": "deno-app",
        "version": "1.0.0",
        "description": "A Deno project",
        "license": "MIT"
    }))
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "deno-app"
    assert identity["project_version"] == "1.0.0"
    assert identity["project_description"] == "A Deno project"
    assert identity["project_license"] == "MIT"
    assert identity["manifest_source"] == "deno.json"

def test_project_identity_deno_jsonc(tmp_path):
    """Test that project identity is correctly detected from deno.jsonc with comments."""
    deno_jsonc = tmp_path / "deno.jsonc"
    deno_jsonc.write_text("""
{
  // This is a comment
  "name": "deno-jsonc-app",
  /* Multi-line
     comment */
  "version": "2.0.0"
}
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "deno-jsonc-app"
    assert identity["project_version"] == "2.0.0"
    assert identity["manifest_source"] == "deno.jsonc"

def test_project_identity_zig_zon(tmp_path):
    """Test that project identity is correctly detected from build.zig.zon."""
    zig_zon = tmp_path / "build.zig.zon"
    # Test both quoted and dot-prefixed name
    zig_zon.write_text("""
.{
    .name = .my_zig_project,
    .version = "0.1.0",
    .paths = .{
        "build.zig",
        "build.zig.zon",
        "src",
    },
}
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "my_zig_project"
    assert identity["project_version"] == "0.1.0"
    assert identity["manifest_source"] == "build.zig.zon"

    # Test quoted name
    zig_zon.write_text("""
.{
    .name = "my-quoted-project",
    .version = "1.2.3"
}
""")
    identity = utils.get_project_identity(tmp_path)
    assert identity["project_name"] == "my-quoted-project"
    assert identity["project_version"] == "1.2.3"

def test_manifest_source_node(tmp_path):
    """Test that manifest_source is correctly set for Node.js."""
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({"name": "node-pkg"}))
    identity = utils.get_project_identity(tmp_path)
    assert identity["manifest_source"] == "package.json"

def test_manifest_source_python(tmp_path):
    """Test that manifest_source is correctly set for Python."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "py-pkg"')
    identity = utils.get_project_identity(tmp_path)
    assert identity["manifest_source"] == "pyproject.toml"
