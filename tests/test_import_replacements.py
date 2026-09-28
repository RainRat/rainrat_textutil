import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import sourcecombine
import utils


class TestImportReplacements(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_import_replacements_json_dict(self):
        config = {"processing": {"regex_replacements": [], "line_regex_replacements": []}}
        rules_file = self.tmp_path / "rules.json"
        rules_file.write_text(
            json.dumps({
                "regex_replacements": [
                    {"pattern": "foo", "replacement": "bar"},
                    ["baz", "qux"]
                ],
                "line_regex_replacements": [
                    {"pattern": "^#.*", "replacement": ""},
                    ["TODO:", "DONE:"]
                ]
            }),
            encoding="utf-8"
        )

        count = sourcecombine.import_replacements(rules_file, config=config)
        self.assertEqual(count, 4)
        self.assertEqual(len(config["processing"]["regex_replacements"]), 2)
        self.assertEqual(config["processing"]["regex_replacements"][0], {"pattern": "foo", "replacement": "bar"})
        self.assertEqual(config["processing"]["regex_replacements"][1], {"pattern": "baz", "replacement": "qux"})
        self.assertEqual(len(config["processing"]["line_regex_replacements"]), 2)
        self.assertEqual(config["processing"]["line_regex_replacements"][0], {"pattern": "^#.*", "replacement": ""})
        self.assertEqual(config["processing"]["line_regex_replacements"][1], {"pattern": "TODO:", "replacement": "DONE:"})

    def test_import_replacements_yaml_list(self):
        config = {"processing": {}}
        rules_file = self.tmp_path / "rules.yaml"
        rules_file.write_text(
            "regex_replacements:\n"
            "  - pattern: 'secret_key'\n"
            "    replacement: '[REDACTED]'\n",
            encoding="utf-8"
        )

        count = sourcecombine.import_replacements(rules_file, config=config)
        self.assertEqual(count, 1)
        self.assertEqual(config["processing"]["regex_replacements"][0], {"pattern": "secret_key", "replacement": "[REDACTED]"})

    def test_import_replacements_none_config(self):
        res = sourcecombine.import_replacements(self.tmp_path / "any.json", config=None)
        self.assertEqual(res, 0)

    def test_import_replacements_empty_source_path(self):
        config = {"processing": {}}
        with self.assertRaises(SystemExit):
            sourcecombine.import_replacements("", config=config)

    def test_import_replacements_missing_file(self):
        config = {"processing": {}}
        with self.assertRaises(SystemExit):
            sourcecombine.import_replacements(self.tmp_path / "nonexistent.json", config=config)

    def test_import_replacements_invalid_content(self):
        config = {"processing": {}}
        bad_file = self.tmp_path / "bad.txt"
        bad_file.write_text("{{{ invalid json/yaml", encoding="utf-8")
        with self.assertRaises(SystemExit):
            sourcecombine.import_replacements(bad_file, config=config)

    def test_import_replacements_stdin(self):
        config = {"processing": {}}
        rules_json = json.dumps({"text_rules": [{"pattern": "cat", "replacement": "dog"}]})

        orig_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(rules_json)
            count = sourcecombine.import_replacements("-", config=config)
            self.assertEqual(count, 1)
            self.assertEqual(config["processing"]["regex_replacements"][0], {"pattern": "cat", "replacement": "dog"})
        finally:
            sys.stdin = orig_stdin

    def test_imported_rules_applied_in_find_and_combine(self):
        sample_file = self.tmp_path / "test.txt"
        sample_file.write_text("Hello secret_pass World", encoding="utf-8")

        rules_file = self.tmp_path / "rules.json"
        rules_file.write_text(
            json.dumps({
                "regex_replacements": [
                    {"pattern": "secret_pass", "replacement": "*****"}
                ]
            }),
            encoding="utf-8"
        )

        out_file = self.tmp_path / "output.txt"
        import copy
        config = copy.deepcopy(utils.DEFAULT_CONFIG)
        utils.validate_config(config)
        config["search"]["root_folders"] = [str(self.tmp_path)]
        config["output"]["file"] = str(out_file)

        sourcecombine.import_replacements(rules_file, config=config)
        sourcecombine.find_and_combine_files(config, str(out_file))

        content = out_file.read_text(encoding="utf-8")
        self.assertIn("Hello ***** World", content)
        self.assertNotIn("secret_pass", content)


if __name__ == "__main__":
    unittest.main()
