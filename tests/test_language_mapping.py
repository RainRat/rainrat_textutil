import sys
from pathlib import Path
import pytest

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import _render_template
from utils import get_language_tag

def test_get_language_tag_extensions():
    assert get_language_tag("file.py") == "python"
    assert get_language_tag("script.js") == "javascript"
    assert get_language_tag("App.tsx") == "typescript"
    assert get_language_tag("styles.scss") == "scss"
    assert get_language_tag("config.yaml") == "yaml"
    assert get_language_tag("main.cpp") == "cpp"
    assert get_language_tag("index.html") == "html"
    assert get_language_tag("archive.tar.gz") == "gz"

def test_get_language_tag_filenames():
    assert get_language_tag("Dockerfile") == "dockerfile"
    assert get_language_tag("Makefile") == "makefile"
    assert get_language_tag("package.json") == "json"
    assert get_language_tag("Cargo.toml") == "toml"
    assert get_language_tag("Jenkinsfile") == "groovy"
    assert get_language_tag("sourcecombine.yml") == "yaml"

def test_get_language_tag_fallback():
    assert get_language_tag("file.unknown") == "unknown"
    assert get_language_tag("no_extension") == "text"

def test_lang_placeholder_rendering():
    template = "Language: {{LANG}}, File: {{FILENAME}}"
    rel_path = Path("src/main.py")

    rendered = _render_template(template, rel_path)
    assert rendered == "Language: python, File: src/main.py"

    rel_path_docker = Path("deploy/Dockerfile")
    rendered = _render_template(template, rel_path_docker)
    assert rendered == "Language: dockerfile, File: deploy/Dockerfile"

def test_markdown_default_header_rendering():
    # Verify that the default Markdown header uses the correct language tag
    template = "## {{FILENAME}}\n\n```{{LANG}}\n"
    rel_path = Path("app.js")

    rendered = _render_template(template, rel_path)
    assert rendered == "## app.js\n\n```javascript\n"
