import json
from pathlib import Path
import sys
import pytest

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sourcecombine import extract_files

def test_extract_text_format(tmp_path):
    """Test extraction from the default SourceCombine text format."""
    output_dir = tmp_path / "extracted"

    content = """--- file1.txt ---
Hello from file 1
--- end file1.txt ---
--- folder/file2.py ---
print("Hello from file 2")
--- end folder/file2.py ---
"""

    extract_files(content, str(output_dir))

    assert (output_dir / "file1.txt").read_text(encoding="utf-8").strip() == "Hello from file 1"
    assert (output_dir / "folder/file2.py").read_text(encoding="utf-8").strip() == 'print("Hello from file 2")'

def test_extract_flexible_markdown(tmp_path):
    """Test extraction from Markdown with different header levels and metadata."""
    output_dir = tmp_path / "extracted"

    content = """# Project Export

## src/main.py
Size: 1.2 KB
Tokens: 300

```python
print("main")
```

### config/settings.yml

```yaml
debug: true
```
"""

    extract_files(content, str(output_dir))

    assert (output_dir / "src/main.py").read_text(encoding="utf-8").strip() == 'print("main")'
    assert (output_dir / "config/settings.yml").read_text(encoding="utf-8").strip() == 'debug: true'

def test_extract_empty_content():
    """Test that empty content raises SystemExit."""
    with pytest.raises(SystemExit):
        extract_files("", "out")

def test_extract_no_matches(caplog):
    """Test logging when no matches are found."""
    content = "Some random text without markers"
    with pytest.raises(SystemExit):
        extract_files(content, "out", source_name="test-source")

    assert "Could not find any files to extract in test-source" in caplog.text
