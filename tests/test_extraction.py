import json
import logging
from pathlib import Path
import pytest
import sys
import os

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import extract_files

def test_extract_json(tmp_path):
    input_file = tmp_path / "combined.json"
    output_dir = tmp_path / "extracted"

    data = [
        {"path": "src/main.py", "content": "print('hello')"},
        {"path": "README.md", "content": "# My Project"}
    ]
    input_file.write_text(json.dumps(data), encoding="utf-8")

    extract_files(str(input_file), str(output_dir))

    assert (output_dir / "src/main.py").read_text(encoding="utf-8") == "print('hello')"
    assert (output_dir / "README.md").read_text(encoding="utf-8") == "# My Project"

def test_extract_xml(tmp_path):
    input_file = tmp_path / "combined.xml"
    output_dir = tmp_path / "extracted"

    content = """<repository>
<file path="app.py">
import os
print("app")
</file>
<file path="config/settings.json">
{"debug": true}
</file>
</repository>"""
    input_file.write_text(content, encoding="utf-8")

    extract_files(str(input_file), str(output_dir))

    # Check app.py
    assert (output_dir / "app.py").read_text(encoding="utf-8") == 'import os\nprint("app")'
    assert (output_dir / "config/settings.json").read_text(encoding="utf-8") == '{"debug": true}'

def test_extract_markdown(tmp_path):
    input_file = tmp_path / "combined.md"
    output_dir = tmp_path / "extracted"

    content = """# Combined Files

## src/utils.py

```python
def add(a, b):
    return a + b
```

## tests/test_utils.py

```python
from utils import add
def test_add():
    assert add(1, 1) == 2
```
"""
    input_file.write_text(content, encoding="utf-8")

    extract_files(str(input_file), str(output_dir))

    assert (output_dir / "src/utils.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b"
    assert (output_dir / "tests/test_utils.py").read_text(encoding="utf-8") == "from utils import add\ndef test_add():\n    assert add(1, 1) == 2"

def test_extract_dry_run(tmp_path):
    input_file = tmp_path / "combined.json"
    output_dir = tmp_path / "extracted"

    data = [{"path": "file.txt", "content": "secret"}]
    input_file.write_text(json.dumps(data), encoding="utf-8")

    extract_files(str(input_file), str(output_dir), dry_run=True)

    assert not (output_dir / "file.txt").exists()

def test_extract_security_traversal(tmp_path):
    input_file = tmp_path / "malicious.json"
    output_dir = tmp_path / "extracted"
    output_dir.mkdir()

    # Attempt to write outside the output folder
    parent_file = tmp_path / "danger.txt"
    data = [{"path": "../danger.txt", "content": "pwned"}]
    input_file.write_text(json.dumps(data), encoding="utf-8")

    extract_files(str(input_file), str(output_dir))

    assert not parent_file.exists()
    assert not (output_dir / "../danger.txt").exists()

def test_extract_unsupported_format(tmp_path, caplog):
    input_file = tmp_path / "random.txt"
    input_file.write_text("just some text", encoding="utf-8")

    with pytest.raises(SystemExit):
        extract_files(str(input_file), str(tmp_path / "out"))

    assert "Could not find any files to extract" in caplog.text
