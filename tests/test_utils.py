import os
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from utils import (
    DEFAULT_CONFIG,
    InvalidConfigError,
    compact_whitespace,
    apply_line_regex_replacements,
    load_and_validate_config,
    process_content,
    read_file_best_effort,
)


def test_compact_whitespace_normalizes_crlf_and_trims():
    raw = "Line 1\r\nLine\t  2\r\n\r\nLine 3   \r\n"
    expected = "Line 1\nLine 2\n\nLine 3\n"
    assert compact_whitespace(raw) == expected


def test_apply_line_regex_replacements_collapses_blocks():
    text = textwrap.dedent(
        """
        keep
        # remove me
        # remove me too
        still here
        # remove again
        done
        """
    ).strip()
    rules = [
        {"pattern": r"^#", "replacement": "<removed>"},
    ]
    result = apply_line_regex_replacements(text, rules)
    assert result == "keep\n<removed>\nstill here\n<removed>\ndone"


def test_process_content_applies_all_options(tmp_path):
    text = "/* header */\nline 1\n/* comment */\nLINE 2\n"
    options = {
        "remove_initial_c_style_comment": True,
        "remove_all_c_style_comments": True,
        "regex_replacements": [
            {"pattern": r"LINE", "replacement": "line"},
        ],
        "line_regex_replacements": [
            {"pattern": r"^line 1$", "replacement": "first"},
        ],
        "compact_whitespace": True,
    }
    result = process_content(text, options)
    assert result == "first\n\nline 2"


def test_read_file_best_effort_handles_various_encodings(tmp_path):
    utf8_bom = "hello"
    bom_file = tmp_path / "utf8_bom.txt"
    bom_file.write_bytes("\ufeff".encode("utf-8") + utf8_bom.encode("utf-8"))

    latin_text = "café"
    latin_file = tmp_path / "latin.txt"
    latin_file.write_bytes(latin_text.encode("cp1252"))

    assert read_file_best_effort(bom_file) == utf8_bom
    assert read_file_best_effort(latin_file) == latin_text


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_and_validate_config_merges_defaults(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
        },
    )
    config = load_and_validate_config(config_path, nested_required={"search": ["root_folders"]})
    assert config["output"]["file"] == DEFAULT_CONFIG["output"]["file"]


def test_load_and_validate_config_rejects_conflicting_options(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {
                "root_folders": ["."],
                "allowed_extensions": [".py"],
            },
            "filters": {
                "inclusion_groups": {
                    "py": {"enabled": True, "filenames": ["*.py"]}
                }
            },
        },
    )
    with pytest.raises(InvalidConfigError):
        load_and_validate_config(config_path)

    pairing_path = _write_config(
        tmp_path,
        {
            "search": {
                "root_folders": ["."],
                "allowed_extensions": [".c"],
            },
            "pairing": {
                "enabled": True,
                "source_extensions": [".c"],
                "header_extensions": [".h"],
            },
        },
    )
    with pytest.raises(InvalidConfigError):
        load_and_validate_config(pairing_path)
