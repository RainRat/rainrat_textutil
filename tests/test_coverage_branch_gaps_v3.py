import sys, os; from pathlib import Path; sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import sourcecombine
import utils


def test_cargo_and_pubspec_repository_fallback(tmp_path):
    cargo_dir = tmp_path / "cargo_proj"
    cargo_dir.mkdir()
    (cargo_dir / "Cargo.toml").write_text(
        '[package]\nname = "cargo-app"\nversion = "0.1.0"\nrepository = "https://github.com/example/cargo-app"\n'
    )
    identity = utils.get_project_identity(cargo_dir)
    assert identity["project_url"] == "https://github.com/example/cargo-app"

    pubspec_dir = tmp_path / "pubspec_proj"
    pubspec_dir.mkdir()
    (pubspec_dir / "pubspec.yaml").write_text(
        'name: pubspec_app\nversion: 1.0.0\nrepository: https://github.com/example/pubspec-app\n'
    )
    identity_pub = utils.get_project_identity(pubspec_dir)
    assert identity_pub["project_url"] == "https://github.com/example/pubspec-app"


def test_readme_empty_or_whitespace_lines_handling(tmp_path):
    readme_dir = tmp_path / "readme_proj"
    readme_dir.mkdir()
    (readme_dir / "README.md").write_text(
        "# My Project\n\n  \n\t\n  \n"
    )
    identity = utils.get_project_identity(readme_dir)
    assert identity["project_name"] == "My Project"
    assert identity["project_description"] == ""


def test_readme_valid_description_after_empty_lines(tmp_path):
    readme_dir = tmp_path / "readme_proj_2"
    readme_dir.mkdir()
    (readme_dir / "README.md").write_text(
        "# My Project\n\n  \n\nFirst actual line of description."
    )
    identity = utils.get_project_identity(readme_dir)
    assert identity["project_name"] == "My Project"
    assert identity["project_description"] == "First actual line of description."


def test_summary_size_primary_metric_branches():
    stats = {
        'discovered_files': 1,
        'total_included': 1,
        'included_files': [('file.bin', 'size')],
        'total_tokens': 100,
        'total_size_bytes': 1024,
        'total_lines': 50,
        'top_files': [(0, 1024, 'file.bin', None, 0, '')],
        'top_folders': [('folder_a', {'tokens': 0, 'size': 1024, 'lines': 0, 'files': 1})],
    }

    mock_args = MagicMock()
    mock_args.quiet = False
    mock_args.format = 'text'

    with patch('shutil.get_terminal_size', return_value=os.terminal_size((120, 24))):
        sourcecombine._print_execution_summary(stats, args=mock_args, pairing_enabled=False, duration=0.1)
