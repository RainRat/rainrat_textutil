import logging
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
    add_line_numbers,
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

    cjk_text = "漢字仮名"
    cjk_file = tmp_path / "cjk_utf16.txt"
    cjk_file.write_bytes(cjk_text.encode("utf-16-le"))

    assert read_file_best_effort(bom_file) == utf8_bom
    assert read_file_best_effort(latin_file) == latin_text
    assert read_file_best_effort(cjk_file) == cjk_text


def test_read_file_best_effort_handles_utf16_edge_cases(tmp_path):
    bom_only = tmp_path / "utf16_bom_only.txt"
    bom_only.write_bytes(b"\xff\xfe")

    without_bom = tmp_path / "utf16_no_bom.txt"
    without_bom.write_bytes("A".encode("utf-16-le"))

    assert read_file_best_effort(bom_only) == ""
    assert read_file_best_effort(without_bom) == "A"


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


def test_load_and_validate_config_rejects_allowed_extensions_with_inclusion_groups(
    tmp_path
):
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

    with pytest.raises(InvalidConfigError) as excinfo:
        load_and_validate_config(config_path)

    assert "mutually exclusive" in str(excinfo.value)

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


def test_inclusion_group_backslashes_are_normalized(tmp_path, caplog):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {
                "inclusion_groups": {
                    "py": {
                        "enabled": True,
                        "filenames": [r"src\\**\\*.py"],
                    }
                }
            },
        },
    )

    with caplog.at_level(logging.WARNING):
        config = load_and_validate_config(config_path)

    filenames = config["filters"]["inclusion_groups"]["py"]["filenames"]
    assert filenames == ["src/**/*.py"]
    assert "uses backslashes" in caplog.text


def test_load_and_validate_config_sets_allowed_extensions_when_pairing_enabled(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "pairing": {
                "enabled": True,
                "source_extensions": [".CPP"],
                "header_extensions": [".H"],
            },
        },
    )
    config = load_and_validate_config(config_path)
    assert config["search"]["effective_allowed_extensions"] == (".cpp", ".h")
    assert "allowed_extensions" not in config["search"]


def test_load_and_validate_config_preserves_user_allowed_extensions(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {
                "root_folders": ["."],
                "allowed_extensions": [".Py"],
            }
        },
    )
    config = load_and_validate_config(config_path)
    assert config["search"]["allowed_extensions"] == [".Py"]
    assert config["search"]["effective_allowed_extensions"] == (".py",)


def test_load_and_validate_config_rejects_non_boolean_skip_binary(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {"skip_binary": "yes"},
        },
    )

    with pytest.raises(InvalidConfigError):
        load_and_validate_config(config_path)


def test_load_and_validate_config_reports_regex_context(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "regex_replacements": [
                    {"pattern": "[unterminated", "replacement": "noop"},
                ]
            },
        },
    )

    with pytest.raises(InvalidConfigError) as excinfo:
        load_and_validate_config(config_path)

    message = str(excinfo.value)
    assert "processing.regex_replacements[0]" in message
    assert str(config_path) in message


def test_load_and_validate_config_reports_line_regex_context(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "line_regex_replacements": [
                    {"pattern": "[unterminated"},
                ]
            },
        },
    )

    with pytest.raises(InvalidConfigError) as excinfo:
        load_and_validate_config(config_path)

    message = str(excinfo.value)
    assert "processing.line_regex_replacements[0]" in message
    assert str(config_path) in message


def test_load_and_validate_config_reports_unterminated_quote(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        'search:\n  root_folders: ["./src]\n',
        encoding="utf-8",
    )

    with pytest.raises(InvalidConfigError) as excinfo:
        load_and_validate_config(config_path)

    message = str(excinfo.value)
    assert "line" in message
    assert "closing quotes" in message


def test_load_and_validate_config_rejects_in_place_groups(tmp_path):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "in_place_groups": {},
            },
        },
    )

    with pytest.raises(InvalidConfigError):
        load_and_validate_config(config_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("min_size_bytes", "10KB"),
        ("min_size_bytes", -1),
        ("max_size_bytes", "10KB"),
        ("max_size_bytes", -1),
    ],
)
def test_load_and_validate_config_rejects_invalid_size_filters(tmp_path, field, value):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {field: value},
        },
    )

    with pytest.raises(InvalidConfigError) as excinfo:
        load_and_validate_config(config_path)

    message = str(excinfo.value)
    assert f"filters.{field}" in message
    assert "non-negative integer" in message


@pytest.mark.parametrize(
    "field",
    [
        "file",
        "folder",
        "header_template",
        "footer_template",
        "global_header_template",
        "global_footer_template",
        "max_size_placeholder",
    ],
)
def test_load_and_validate_config_rejects_non_string_output_fields(tmp_path, field):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {field: 123},
        },
    )

    with pytest.raises(InvalidConfigError) as excinfo:
        load_and_validate_config(config_path)

    assert f"output.{field}" in str(excinfo.value)


def test_load_and_validate_config_warns_on_placeholder_missing_filename(tmp_path, caplog):
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {"max_size_placeholder": "File is too large"},
        },
    )

    with caplog.at_level(logging.WARNING):
        load_and_validate_config(config_path)

    assert "does not include the {{FILENAME}} placeholder" in caplog.text

def test_add_line_numbers():
    assert add_line_numbers("a\nb") == "1: a\n2: b"
    assert add_line_numbers("") == ""
    assert add_line_numbers("hello") == "1: hello"
    assert add_line_numbers("a\n") == "1: a\n"
    assert add_line_numbers("a\nb\n") == "1: a\n2: b\n"


def test_compact_whitespace_converts_spaces_to_tabs():
    assert compact_whitespace("line\n    indent") == "line\n\tindent"
    assert compact_whitespace(" " * 8) == "\t\t"
    assert compact_whitespace(" " * 5) == "\t "


def test_compact_whitespace_removes_spaces_around_tabs():
    assert compact_whitespace("\n\t  indent") == "\n\tindent"
    assert compact_whitespace("indent  \t\n") == "indent\n"


def test_compact_whitespace_replaces_standalone_tabs():
    assert compact_whitespace("a\tb") == "a b"


def test_compact_whitespace_collapses_long_space_runs():
    assert compact_whitespace("a   b") == "a  b"


def test_compact_whitespace_handles_mixed_indent_tabs_and_spaces():
    assert compact_whitespace("  \t  code") == "\tcode"
    assert compact_whitespace("\t    code") == "\t\tcode"


def test_compact_whitespace_groups_can_disable_transformations():
    original = "Line\r\n    ind\t  ent\n\n\ntrail   "
    overrides = {
        "normalize_line_endings": False,
        "spaces_to_tabs": False,
        "trim_spaces_around_tabs": False,
        "replace_mid_line_tabs": False,
        "trim_trailing_whitespace": False,
        "compact_blank_lines": False,
        "compact_space_runs": False,
    }
    assert compact_whitespace(original, groups=overrides) == original


def test_process_content_compact_whitespace_overrides_enable_specific_group():
    text = "a   b\n\n\n"
    options = {
        "compact_whitespace": False,
        "compact_whitespace_groups": {
            "compact_space_runs": True,
            "compact_blank_lines": True,
        },
    }
    assert process_content(text, options) == "a  b\n\n"


def test_process_content_compact_whitespace_overrides_can_disable_group():
    text = "a\tb"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "replace_mid_line_tabs": False,
        },
    }
    assert process_content(text, options) == text


def test_validate_glob_pattern_warns_on_absolute_paths(caplog, tmp_path):
    load_and_validate_config(
        _write_config(
            tmp_path,
            {
                "search": {"root_folders": ["."]},
                "filters": {
                    "exclusions": {
                        "filenames": ["/abs/path/*"],
                    },
                },
            },
        )
    )
    assert "looks like an absolute path" in caplog.text


def test_validate_glob_pattern_warns_on_regex_like_syntax(caplog, tmp_path):
    load_and_validate_config(
        _write_config(
            tmp_path,
            {
                "search": {"root_folders": ["."]},
                "filters": {
                    "inclusion_groups": {
                        "group1": {
                            "enabled": True,
                            "filenames": ["(a|b)+.txt"],
                        },
                    },
                },
            },
        )
    )
    assert "regular expression syntax" in caplog.text


def test_validate_glob_pattern_raises_on_non_string_pattern(tmp_path):
    with pytest.raises(InvalidConfigError, match="must be a string"):
        load_and_validate_config(
            _write_config(
                tmp_path,
                {
                    "search": {"root_folders": ["."]},
                    "filters": {
                        "exclusions": {
                            "filenames": [123],
                        },
                    },
                },
            )
        )
