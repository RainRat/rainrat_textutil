import sys
import unittest
from pathlib import Path
from io import StringIO
import sourcecombine

class TestLineLimit(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = Path("temp_test_line_limit")
        self.test_dir.mkdir(exist_ok=True)

        # Create some test files
        (self.test_dir / "file1.txt").write_text("line1\nline2\nline3\n", encoding="utf-8") # 3 lines
        (self.test_dir / "file2.txt").write_text("line4\nline5\n", encoding="utf-8") # 2 lines
        (self.test_dir / "file3.txt").write_text("line6\n", encoding="utf-8") # 1 line

        # Standard header/footer adds 2 lines by default in SourceCombine
        # Header: --- file1.txt ---
        # Footer: \n--- end file1.txt ---
        # Total per file: content + 2 lines

    def tearDown(self):
        # Clean up temporary directory
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_line_limit_truncation(self):
        config = {
            'search': {'root_folders': [str(self.test_dir)], 'recursive': False},
            'filters': {'max_total_lines': 8}, # file1 is 3 content + 2 template = 5. file2 is 2 content + 2 template = 4. Total 9. Limit 8 should skip file2.
            'output': {
                'file': 'combined.txt',
                'header_template': "--- {{FILENAME}} ---\n",
                'footer_template': "\n--- end {{FILENAME}} ---\n",
                'sort_by': 'name'
            }
        }

        # Use a temporary output file
        out_path = self.test_dir / "output.txt"

        stats = sourcecombine.find_and_combine_files(
            config,
            str(out_path),
            dry_run=False
        )

        # file1 (3 content lines + 2 boundary lines) = 5 lines.
        # file2 (2 content lines + 2 boundary lines) = 4 lines.
        # Total 9 lines. Limit 8.
        # It should only include file1.

        self.assertEqual(stats['total_files'], 1)
        self.assertTrue(stats['line_limit_reached'])
        self.assertEqual(stats['filter_reasons']['line_limit'], 2) # file2 and file3 skipped

        content = out_path.read_text(encoding="utf-8")
        self.assertIn("file1.txt", content)
        self.assertNotIn("file2.txt", content)
        self.assertNotIn("file3.txt", content)

    def test_line_limit_usage_summary(self):
        # Mock sys.stderr to capture summary output
        stderr_capture = StringIO()
        original_stderr = sys.stderr
        sys.stderr = stderr_capture

        try:
            stats = {
                'total_files': 1,
                'total_discovered': 3,
                'total_size_bytes': 100,
                'total_tokens': 25,
                'total_lines': 5,
                'max_total_lines': 10,
                'line_limit_reached': False,
                'filter_reasons': {'line_limit': 2},
                'files_by_extension': {'.txt': 1}
            }
            args = type('Args', (), {'dry_run': False, 'estimate_tokens': False, 'list_files': False, 'tree': False, 'extract': False})()

            sourcecombine._print_execution_summary(stats, args, pairing_enabled=False)

            summary = stderr_capture.getvalue()
            self.assertIn("Line Limit Usage:", summary)
            self.assertIn("[#####-----]", summary) # 50%
            self.assertIn("50.0%", summary)
        finally:
            sys.stderr = original_stderr

if __name__ == '__main__':
    unittest.main()
