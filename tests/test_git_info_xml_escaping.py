import unittest
from unittest.mock import patch
from pathlib import Path
import sourcecombine

class TestGitInfoXmlEscaping(unittest.TestCase):
    def test_git_info_with_xml_escaping(self):
        # A filename that contains an XML-special character
        rel_path = Path("src/main & test.py")

        # Mock git_info
        git_info = {
            'git_repo_root': '/tmp/repo',
            'git_commit': 'abcdef1',
            'git_remote_url': 'https://github.com/user/repo',
            'file_statuses': {rel_path.as_posix(): 'M'},
            'file_diffs': {rel_path.as_posix(): 'diff content'}
        }

        # Mock _get_file_git_info to return something if the correct filename is passed
        def side_effect(path, repo_root):
            if path == rel_path.as_posix():
                return {'file_author': 'John Doe'}
            return {}

        with patch('sourcecombine._get_file_git_info', side_effect=side_effect):
            # Template that uses git placeholders
            template = "{{FILENAME}} Author: {{FILE_AUTHOR}} Status: {{FILE_STATUS}}"

            # XML escaping
            result_xml = sourcecombine._render_template(
                template, rel_path, git_info=git_info, escape_func=sourcecombine.xml_escape
            )

            # The filename in the output should be escaped
            self.assertIn("src/main &amp; test.py", result_xml)

            # Git info and status should still be resolved
            self.assertIn("John Doe", result_xml)
            self.assertIn("Status: M", result_xml)

if __name__ == '__main__':
    unittest.main()
