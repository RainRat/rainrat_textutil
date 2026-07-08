import sys; import os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import unittest
from unittest.mock import patch, MagicMock
import argparse
import sourcecombine

class TestAnalyzeFeature(unittest.TestCase):
    def _create_mock_args(self, analyze=True):
        args = argparse.Namespace()
        # Essential flags for main() to run without AttributeError
        args.targets = []
        args.analyze = analyze
        args.ai = False
        args.dry_run = False
        args.estimate_tokens = False
        args.overview = False
        args.include_tree = False
        args.tree = False
        args.verbose = False
        args.config = None
        args.extract = False
        args.verify = False
        args.system_info = False
        args.project_info = False
        args.list_placeholders = False
        args.list_languages = False
        args.init = False
        args.restore = False
        args.delete_backups = False
        args.files_from = None
        args.exclude_file = []
        args.exclude_folder = []
        args.include = []
        args.map_lang = []
        args.extension = []
        args.exclude_extension = []
        args.language = []
        args.exclude_language = []
        args.pair = []
        args.include_unpaired = False
        args.pair_template = None
        args.output = None
        args.max_tokens = None
        args.max_total_size = None
        args.min_tokens = None
        args.max_file_tokens = None
        args.min_lines = None
        args.max_file_lines = None
        args.max_total_lines = None
        args.limit = None
        args.max_depth = None
        args.grep = None
        args.exclude_grep = None
        args.skip_binary = False
        args.unique = False
        args.git_files = False
        args.git_diff = False
        args.staged = False
        args.unstaged = False
        args.since = None
        args.until = None
        args.min_size = None
        args.max_size = None
        args.toc = False
        args.json_summary = None
        args.mirror = False
        args.no_content = False
        args.line_numbers = False
        args.git_log = None
        args.include_diff = False
        args.header = None
        args.footer = None
        args.global_header = None
        args.global_footer = None
        args.max_size_placeholder = None
        args.markdown = False
        args.json = False
        args.jsonl = False
        args.xml = False
        args.csv = False
        args.sort = None
        args.reverse = False
        args.show_config = False
        args.export_config = None
        args.diff = False
        args.compact = False
        args.apply_in_place = False
        args.create_backups = False
        args.remove_comments = False
        args.remove_single_line_comments = False
        args.max_lines = None
        args.truncate_tokens = None
        args.replace = []
        args.replace_line = []
        args.keep_line_numbers = False
        args.repair = False
        args.clean = False
        args.preview = False
        args.strip_components = 0
        args.project_name = None
        args.project_version = None
        args.project_description = None
        args.project_license = None
        args.project_url = None
        args.format = None
        args.clipboard = False
        args.list_files = False
        return args

    @patch('argparse.ArgumentParser.parse_args')
    def test_analyze_preset_expansion(self, mock_parse_args):
        mock_args = self._create_mock_args(analyze=True)
        mock_parse_args.return_value = mock_args

        with patch('sourcecombine.load_and_validate_config'), \
             patch('sourcecombine.find_and_combine_files'), \
             patch('sourcecombine._print_execution_summary'), \
             patch('logging.getLogger'), \
             patch('sys.exit'):

            sourcecombine.main()

            self.assertTrue(mock_args.dry_run)
            self.assertTrue(mock_args.estimate_tokens)
            self.assertTrue(mock_args.overview)
            self.assertTrue(mock_args.include_tree)
            self.assertTrue(mock_args.tree)

    @patch('argparse.ArgumentParser.parse_args')
    def test_analyze_preset_disabled(self, mock_parse_args):
        mock_args = self._create_mock_args(analyze=False)
        mock_parse_args.return_value = mock_args

        with patch('sourcecombine.load_and_validate_config'), \
             patch('sourcecombine.find_and_combine_files'), \
             patch('sourcecombine._print_execution_summary'), \
             patch('logging.getLogger'), \
             patch('sys.exit'):

            sourcecombine.main()

            self.assertFalse(mock_args.dry_run)
            self.assertFalse(mock_args.estimate_tokens)
            self.assertFalse(mock_args.overview)
            self.assertFalse(mock_args.include_tree)
            self.assertFalse(mock_args.tree)

if __name__ == '__main__':
    unittest.main()
