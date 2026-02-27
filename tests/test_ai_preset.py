import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse

# Add current directory to sys.path to import sourcecombine
sys.path.append(str(Path(__file__).parent.parent))
import sourcecombine

class TestAIPreset(unittest.TestCase):
    @patch('argparse.ArgumentParser.parse_args')
    @patch('importlib.util.find_spec')
    def test_ai_preset_expansion(self, mock_find_spec, mock_parse_args):
        # Set up mock arguments
        mock_args = argparse.Namespace(
            targets=[],
            ai=True,
            markdown=False,
            json=False,
            xml=False,
            format=None,
            line_numbers=False,
            toc=False,
            include_tree=False,
            output=None,
            clipboard=False,
            dry_run=False,
            list_files=False,
            tree=False,
            estimate_tokens=False,
            verbose=False,
            exclude_file=[],
            exclude_folder=[],
            include=[],
            since=None,
            until=None,
            limit=None,
            max_tokens=None,
            files_from=None,
            compact=False,
            sort=None,
            reverse=False,
            extract=False,
            system_info=False,
            init=False,
            grep=None
        )
        mock_parse_args.return_value = mock_args
        mock_find_spec.return_value = MagicMock() # Simulate pyperclip installed

        # Mock dependencies to prevent main() from doing real work or exiting
        with patch('sourcecombine.load_and_validate_config'), \
             patch('sourcecombine.find_and_combine_files'), \
             patch('sourcecombine._print_execution_summary'), \
             patch('logging.getLogger'), \
             patch('sys.exit'):

            sourcecombine.main()

            # Check if flags were updated in the mock_args object
            self.assertTrue(mock_args.markdown)
            self.assertTrue(mock_args.line_numbers)
            self.assertTrue(mock_args.toc)
            self.assertTrue(mock_args.include_tree)
            self.assertTrue(mock_args.clipboard)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('importlib.util.find_spec')
    def test_ai_preset_no_clipboard_if_output_provided(self, mock_find_spec, mock_parse_args):
        mock_args = argparse.Namespace(
            targets=[],
            ai=True,
            markdown=False,
            json=False,
            xml=False,
            format=None,
            line_numbers=False,
            toc=False,
            include_tree=False,
            output='out.txt',
            clipboard=False,
            dry_run=False,
            list_files=False,
            tree=False,
            estimate_tokens=False,
            verbose=False,
            exclude_file=[],
            exclude_folder=[],
            include=[],
            since=None,
            until=None,
            limit=None,
            max_tokens=None,
            files_from=None,
            compact=False,
            sort=None,
            reverse=False,
            extract=False,
            system_info=False,
            init=False,
            grep=None
        )
        mock_parse_args.return_value = mock_args
        mock_find_spec.return_value = MagicMock()

        with patch('sourcecombine.load_and_validate_config'), \
             patch('sourcecombine.find_and_combine_files'), \
             patch('sourcecombine._print_execution_summary'), \
             patch('logging.getLogger'), \
             patch('sys.exit'):

            sourcecombine.main()

            self.assertTrue(mock_args.markdown)
            self.assertFalse(mock_args.clipboard)

    @patch('argparse.ArgumentParser.parse_args')
    @patch('importlib.util.find_spec')
    def test_ai_preset_no_clipboard_if_no_pyperclip(self, mock_find_spec, mock_parse_args):
        mock_args = argparse.Namespace(
            targets=[],
            ai=True,
            markdown=False,
            json=False,
            xml=False,
            format=None,
            line_numbers=False,
            toc=False,
            include_tree=False,
            output=None,
            clipboard=False,
            dry_run=False,
            list_files=False,
            tree=False,
            estimate_tokens=False,
            verbose=False,
            exclude_file=[],
            exclude_folder=[],
            include=[],
            since=None,
            until=None,
            limit=None,
            max_tokens=None,
            files_from=None,
            compact=False,
            sort=None,
            reverse=False,
            extract=False,
            system_info=False,
            init=False,
            grep=None
        )
        mock_parse_args.return_value = mock_args
        mock_find_spec.return_value = None # Simulate pyperclip NOT installed

        with patch('sourcecombine.load_and_validate_config'), \
             patch('sourcecombine.find_and_combine_files'), \
             patch('sourcecombine._print_execution_summary'), \
             patch('logging.getLogger'), \
             patch('sys.exit'):

            sourcecombine.main()

            self.assertTrue(mock_args.markdown)
            self.assertFalse(mock_args.clipboard)

if __name__ == '__main__':
    unittest.main()
