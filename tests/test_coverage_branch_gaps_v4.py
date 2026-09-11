import copy
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

import utils
from utils import get_project_identity
from sourcecombine import find_and_combine_files, main


def test_cargo_repository_fallback_when_url_preset(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project.urls]\nhomepage = "http://homepage.com"\n', encoding="utf-8"
    )
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "cargo_pkg"\nrepository = "http://cargo-repo.com"\n',
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "http://homepage.com"


def test_pubspec_repository_fallback_when_url_preset(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project.urls]\nhomepage = "http://homepage.com"\n', encoding="utf-8"
    )
    (tmp_path / "pubspec.yaml").write_text(
        "name: pub_pkg\nrepository: http://pub-repo.com\n", encoding="utf-8"
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_url"] == "http://homepage.com"


def test_readme_parsing_leading_header_and_empty_lines(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Project Header\n\n   \n\n   \n## Subheader\nFirst content paragraph.",
        encoding="utf-8",
    )
    identity = get_project_identity(tmp_path)
    assert identity["project_name"] == "Project Header"
    assert identity["project_description"] == ""


def test_pairing_file_limit_and_placeholder(tmp_path):
    f1_src = tmp_path / "src1.cpp"
    f1_hdr = tmp_path / "src1.h"
    f1_src.write_text("int x = 1;", encoding="utf-8")
    f1_hdr.write_text("extern int x;", encoding="utf-8")

    f2_src = tmp_path / "src2.cpp"
    f2_hdr = tmp_path / "src2.h"
    f2_src.write_text("int y = 2;", encoding="utf-8")
    f2_hdr.write_text("extern int y;", encoding="utf-8")

    config = copy.deepcopy(utils.DEFAULT_CONFIG)
    config["search"]["root_folders"] = [str(tmp_path)]
    config["filters"]["max_files"] = 1
    config["pairing"]["enabled"] = True
    config["pairing"]["source_extensions"] = [".cpp"]
    config["pairing"]["header_extensions"] = [".h"]
    config["output"]["format"] = "text"
    config["output"]["max_size_placeholder"] = "[TRUNCATED MAX SIZE]"

    output_file = tmp_path / "out.txt"
    stats = find_and_combine_files(config, output_path=output_file)
    assert stats["limit_reached"] is True
    assert stats["filter_reasons"]["file_limit"] == 1


def test_cli_exclude_file_empty_tokens(tmp_path):
    config_file = tmp_path / "config.yml"
    config_file.write_text("search: {root_folders: ['.']}", encoding="utf-8")

    mock_stats = {
        "total_files": 0,
        "total_discovered": 0,
        "total_size_bytes": 0,
        "files_by_language": {},
        "total_tokens": 0,
        "token_count_is_approx": False,
        "top_files": [],
        "filter_reasons": {},
    }

    orig_validate_config = utils.validate_config

    def side_effect_validate(config, *args, **kwargs):
        return orig_validate_config(config, *args, **kwargs)

    with patch("utils.validate_config", side_effect=side_effect_validate):
        with patch("sourcecombine.validate_config", return_value=None):
            with patch("sourcecombine.find_and_combine_files", return_value=mock_stats) as mock_combine:
                with patch.object(
                    sys,
                    "argv",
                    ["sourcecombine.py", str(config_file), "--exclude-file", ",,  ,file.txt"],
                ):
                    main()

    args, _ = mock_combine.call_args
    passed_config = args[0]
    assert "file.txt" in passed_config["filters"]["exclusions"]["filenames"]
