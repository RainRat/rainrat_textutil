import pytest
from pathlib import Path
import utils
import sourcecombine

def test_collapsible_markdown_generation(tmp_path, monkeypatch):
    file1 = tmp_path / "foo.py"
    file1.write_text("print('hello')", encoding="utf-8")

    file2 = tmp_path / "bar.js"
    file2.write_text("console.log('world');", encoding="utf-8")

    output_file = tmp_path / "combined.md"

    monkeypatch.setattr('sys.argv', [
        'sourcecombine.py',
        str(file1),
        str(file2),
        '--format', 'markdown',
        '--collapsible',
        '--output', str(output_file)
    ])

    try:
        sourcecombine.main()
    except SystemExit as excinfo:
        assert excinfo.code == 0

    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")

    assert "<details>" in content
    assert "</details>" in content
    assert "<summary>foo.py</summary>" in content
    assert "<summary>bar.js</summary>" in content
    assert "print('hello')" in content
    assert "console.log('world');" in content

def test_collapsible_markdown_extraction(tmp_path, monkeypatch):
    combined_content = """
<details>
<summary>src/first.py</summary>

```python
def first():
    pass
```

</details>

<details>
<summary>src/second.js</summary>

```javascript
function second() {}
```

</details>
"""
    combined_file = tmp_path / "combined.md"
    combined_file.write_text(combined_content, encoding="utf-8")

    output_dir = tmp_path / "restored"

    monkeypatch.setattr('sys.argv', [
        'sourcecombine.py',
        '--extract',
        str(combined_file),
        '--output', str(output_dir)
    ])

    try:
        sourcecombine.main()
    except SystemExit as excinfo:
        assert excinfo.code == 0

    assert (output_dir / "src" / "first.py").exists()
    assert (output_dir / "src" / "second.js").exists()

    assert (output_dir / "src" / "first.py").read_text(encoding="utf-8").strip() == "def first():\n    pass"
    assert (output_dir / "src" / "second.js").read_text(encoding="utf-8").strip() == "function second() {}"

def test_collapsible_invalid_format_raises_error(tmp_path, monkeypatch):
    file1 = tmp_path / "foo.py"
    file1.write_text("print('hello')", encoding="utf-8")
    output_file = tmp_path / "combined.txt"

    monkeypatch.setattr('sys.argv', [
        'sourcecombine.py',
        str(file1),
        '--format', 'text',
        '--collapsible',
        '--output', str(output_file)
    ])

    with pytest.raises(SystemExit) as excinfo:
        sourcecombine.main()

    assert excinfo.value.code == 1

def test_parse_combined_content_with_summaries():
    content = """
<details>
<summary>a.py</summary>

```python
import os
```

</details>
"""
    parsed = sourcecombine._parse_combined_content(content)
    assert len(parsed) == 1
    assert parsed[0][0] == "a.py"
    assert parsed[0][1].strip() == "import os"
