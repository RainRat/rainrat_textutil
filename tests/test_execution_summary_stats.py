import os
import sys
import pytest
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
import sourcecombine

def test_language_stats_reset_with_limit(tmp_path):
    """Verify that language stats are correctly reset when a file limit is applied."""
    # Create a project with 3 files of two different languages
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Standard alphabetical sort order: main.py, styles.css, utils.py
    file1 = project_dir / "main.py"
    file1.write_text("print('hello')\nprint('world')") # 2 lines

    file2 = project_dir / "styles.css"
    file2.write_text("body { color: red; }") # 1 line

    file3 = project_dir / "utils.py"
    file3.write_text("def foo(): pass") # 1 line

    # Run sourcecombine with a limit of 2 files and overview enabled
    # With limit 2: main.py and styles.css should be included.
    # Included: 2 files. 1 python, 1 css.

    output_file = tmp_path / "combined.txt"

    with patch("sys.stdout", new=MagicMock()) as mock_stdout, \
         patch("sys.stderr", new=MagicMock()) as mock_stderr:

        args = [
            "sourcecombine.py",
            str(project_dir),
            "--limit", "2",
            "--overview",
            "--output", str(output_file)
        ]

        with patch.object(sys, 'argv', args):
            sourcecombine.main()

        # Get stderr output which contains the execution summary
        stderr_output = "".join(call.args[0] for call in mock_stderr.write.call_args_list)

        # Clean up ANSI escape sequences for easier parsing
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', stderr_output)

        print(clean_output)

        # Verify that Included files is 2
        assert re.search(r"Included:\s+2 files", clean_output)

        # Look for "python" and check preceding numbers
        # If buggy: it will show more than 1 file for python because it adds to previous stats.
        # New layout: ... [DISTRIBUTION] FILES % FILES LANGUAGE
        python_match = re.search(r'(\d+)\s+([\d.]+)%\s+python', clean_output)
        assert python_match, "Could not find python in Languages table"

        count = int(python_match.group(1))
        # percent = float(python_match.group(2)) # Percentage might be weird if bug exists

        assert count == 1, f"Expected 1 python file, got {count}. Stats were likely not reset."
