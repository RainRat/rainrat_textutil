import unittest
from pathlib import Path
from unittest.mock import patch
import sourcecombine

class TestAnsiLeak(unittest.TestCase):
    def test_generate_tree_string_ansi_leak_in_markdown(self):
        # Setup paths and metadata
        root_path = Path("root")
        paths = [root_path / "file1.txt"]
        metadata = {
            root_path / "file1.txt": {"size": 1024, "tokens": 256, "lines": 50}
        }

        # Force NO_COLOR to be empty so colors can trigger
        with patch.dict("os.environ", {"NO_COLOR": ""}):
            # Mock isatty to simulate a terminal environment
            with patch("sys.stderr.isatty", return_value=True), \
                 patch("sys.stdout.isatty", return_value=True):

                # Generate tree string in Markdown format
                tree_output = sourcecombine._generate_tree_string(
                    paths, root_path, output_format="markdown", metadata=metadata
                )

                # ANSI escape code pattern
                ansi_escape = sourcecombine._ANSI_ESCAPE

                # Check if ANSI codes are present
                has_ansi = bool(ansi_escape.search(tree_output))

                print(f"\nTree output with format='markdown':\n{tree_output}")

                self.assertFalse(has_ansi, "Markdown output should not contain ANSI escape codes")

    def test_generate_tree_string_ansi_present_in_text(self):
        # Setup paths and metadata
        root_path = Path("root")
        paths = [root_path / "file1.txt"]
        metadata = {
            root_path / "file1.txt": {"size": 1024, "tokens": 256, "lines": 50}
        }

        # Force NO_COLOR to be empty so colors can trigger
        with patch.dict("os.environ", {"NO_COLOR": ""}):
            # Mock isatty to simulate a terminal environment
            with patch("sys.stderr.isatty", return_value=True), \
                 patch("sys.stdout.isatty", return_value=True):

                # Generate tree string in text format
                tree_output = sourcecombine._generate_tree_string(
                    paths, root_path, output_format="text", metadata=metadata
                )

                # ANSI escape code pattern
                ansi_escape = sourcecombine._ANSI_ESCAPE

                # Check if ANSI codes are present
                has_ansi = bool(ansi_escape.search(tree_output))

                print(f"\nTree output with format='text':\n{tree_output}")

                self.assertTrue(has_ansi, "Text output SHOULD contain ANSI escape codes in terminal")

if __name__ == "__main__":
    unittest.main()
