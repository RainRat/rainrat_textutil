import hashlib
from pathlib import Path
import sourcecombine

def test_render_template_uses_precalculated_hash():
    template = "Hash: {{HASH}}"
    sha256 = "dummy_hash"
    rendered = sourcecombine._render_template(template, Path("test.py"), sha256=sha256)
    assert rendered == "Hash: dummy_hash"

def test_render_template_calculates_content_hash():
    template = "Hash: {{HASH}}"
    content = "print('hello')"
    expected = hashlib.sha256(content.encode('utf-8')).hexdigest()

    rendered = sourcecombine._render_template(template, Path("test.py"), content=content)
    assert rendered == f"Hash: {expected}"

def test_render_template_handles_missing_content_for_hash():
    template = "Hash: {{HASH}}"
    rendered = sourcecombine._render_template(template, Path("test.py"))
    assert rendered == "Hash: "
