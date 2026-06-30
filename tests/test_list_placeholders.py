import unittest
from unittest.mock import patch, MagicMock
import io
import sys
from sourcecombine import print_placeholders

class TestListPlaceholders(unittest.TestCase):
    def test_print_placeholders(self):
        captured_output = io.StringIO()
        sys.stdout = captured_output
        try:
            print_placeholders()
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("=== TEMPLATE PLACEHOLDERS ===", output)
        self.assertIn("File-Level Placeholders", output)
        self.assertIn("{{FILENAME}}", output)
        self.assertIn("Project Information (Global) Placeholders", output)
        self.assertIn("{{FILE_COUNT}}", output)
        self.assertIn("Git Placeholders", output)
        self.assertIn("{{GIT_BRANCH}}", output)
        self.assertIn("System & Environment Placeholders", output)
        self.assertIn("{{OS}}", output)
        self.assertIn("Pairing-Specific Placeholders", output)
        self.assertIn("{{SOURCE_EXT}}", output)

if __name__ == '__main__':
    unittest.main()
