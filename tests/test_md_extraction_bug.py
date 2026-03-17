import os
import sys
import copy

# Ensure we can import sourcecombine and utils
sys.path.append(os.getcwd())

import sourcecombine
import utils

def test_md_header_selection():
    content = """
## Project Overview
This is some general information about the project.

## src/main.py
```python
print("hello world")
```

## src/utils.py
```python
def some_util():
    pass
```
"""
    config = copy.deepcopy(utils.DEFAULT_CONFIG)

    # We use extract_files in dry_run mode to avoid writing to disk
    # and just inspect the returned stats.
    stats = sourcecombine.extract_files(
        content,
        "dummy_output",
        dry_run=True,
        config=config,
        source_name="test_content.md"
    )

    extracted_paths = [path for _, _, path in stats['top_files']]

    print(f"Extracted paths: {extracted_paths}")

    # The bug: "Project Overview" is taken instead of "src/main.py"
    # Expected: ["src/main.py", "src/utils.py"]
    # Actual (buggy): ["Project Overview", "src/utils.py"]

    assert "src/main.py" in extracted_paths, f"Missing src/main.py, found {extracted_paths}"
    assert "src/utils.py" in extracted_paths, f"Missing src/utils.py, found {extracted_paths}"
    assert "Project Overview" not in extracted_paths, "Incorrectly extracted 'Project Overview' header"

if __name__ == "__main__":
    try:
        test_md_header_selection()
        print("Test passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
