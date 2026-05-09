import sys
import os
from pathlib import Path
from unittest.mock import patch
import pytest
import yaml
import sourcecombine
from sourcecombine import main, _render_template, extract_files
from utils import get_project_name

def test_main_template_overrides_via_cli(capsys):
    """Cover sourcecombine.py lines 4235, 4237, 4239, 4241, 4243."""
    args = [
        "sourcecombine.py",
        "--header", "H_OVR",
        "--footer", "F_OVR",
        "--global-header", "GH_OVR",
        "--global-footer", "GF_OVR",
        "--max-size-placeholder", "MSP_OVR",
        "--show-config"
    ]
    with patch("sys.argv", args):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    config = yaml.safe_load(captured.out)
    assert config["output"]["header_template"] == "H_OVR"
    assert config["output"]["footer_template"] == "F_OVR"
    assert config["output"]["global_header_template"] == "GH_OVR"
    assert config["output"]["global_footer_template"] == "GF_OVR"
    assert config["output"]["max_size_placeholder"] == "MSP_OVR"

def test_main_files_from_empty_lines(tmp_path):
    """Cover sourcecombine.py branch 4270->4268."""
    list_file = tmp_path / "files.txt"
    # File with empty lines and spaces
    list_file.write_text("\n  \nfile.txt\n\n", encoding="utf-8")
    (tmp_path / "file.txt").write_text("content", encoding="utf-8")

    args = ["sourcecombine.py", str(tmp_path), "--files-from", str(list_file), "--dry-run"]
    with patch("sys.argv", args):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

def test_extract_files_empty_json_list():
    """Cover sourcecombine.py branch 4517->4523."""
    # JSON content that is an empty list should skip the "if files_found" return
    # and proceed to try JSONL parsing.
    content = "[]"
    with patch("sourcecombine.Path.exists", return_value=True), \
         patch("sourcecombine.Path.is_file", return_value=True), \
         patch("sourcecombine.utils.read_file_best_effort", return_value=(content, "utf-8")):
        # It should exit because no files are found after JSON and JSONL attempts
        with pytest.raises(SystemExit) as exc:
            # Sources must be a list of (name, content)
            extract_files([("dummy.json", content)], "output_folder")
        assert exc.value.code == 1

def test_get_project_name_empty_package_json(tmp_path):
    """Cover utils.py branch 1318->1324."""
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text("{}", encoding="utf-8")
    # Should skip name-less package.json and fallback to folder name
    assert get_project_name(tmp_path) == tmp_path.name

def test_render_template_missing_git_info():
    """Cover sourcecombine.py branch 549->559."""
    template = "{{FILE_URL}}"
    # git_info has remote_url but missing git_commit
    git_info = {
        "git_remote_url": "https://github.com/user/repo",
        "git_commit": None,
        "git_repo_root": "/tmp/repo"
    }
    # relative_path must be a Path object to have as_posix()
    result = _render_template(template, Path("file.txt"), git_info=git_info)
    # Since commit is missing, branch 549->559 is taken, replacements["{{FILE_URL}}"] is NOT set.
    # _render_single_pass will return the template with the placeholder untouched if it's not in replacements.
    assert result == "{{FILE_URL}}"
