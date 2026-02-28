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
    format_size,
    validate_config,
    _validate_pairing_section,
    load_yaml_config,
    _validate_regex_list,
    _validate_glob_list,
    validate_glob_pattern,
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
    assert result == "first\n\nline 2\n"


def test_read_file_best_effort_handles_various_encodings(tmp_path):
    utf8_bom = "hello"
    bom_file = tmp_path / "utf8_bom.txt"
    bom_file.write_bytes("\ufeff".encode("utf-8") + utf8_bom.encode("utf-8"))

    latin_text = "café"
    latin_file = tmp_path / "latin.txt"
    latin_file.write_bytes(latin_text.encode("cp1252"))

    cjk_text = "漢字仮名"
    cjk_file = tmp_path / "cjk_utf16.txt"
    cjk_file.write_bytes(cjk_text.encode("utf-16"))

    content, _ = read_file_best_effort(bom_file)
    assert content == utf8_bom
    content, _ = read_file_best_effort(latin_file)
    assert content == latin_text
    content, _ = read_file_best_effort(cjk_file)
    assert content == cjk_text


def test_read_file_best_effort_handles_utf16_edge_cases(tmp_path):
    bom_only = tmp_path / "utf16_bom_only.txt"
    bom_only.write_bytes(b"\xff\xfe")

    without_bom = tmp_path / "utf16_no_bom.txt"
    without_bom.write_bytes("A".encode("utf-16-le"))

    content, _ = read_file_best_effort(bom_only)
    assert content == ""
    content, _ = read_file_best_effort(without_bom)
    assert content == "A"


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

    assert "cannot be used at the same time" in str(excinfo.value)

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
    assert "0 or more" in message


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
    assert compact_whitespace(" " * 8 + "content") == "\t\tcontent"
    assert compact_whitespace(" " * 5 + "content") == "\tcontent"


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

def test_compact_whitespace_trims_trailing_whitespace_on_last_line_no_newline():
    assert compact_whitespace("abc  ") == "abc"

def test_compact_whitespace_trims_trailing_tabs_on_last_line_no_newline():
    assert compact_whitespace("abc\t") == "abc"

def test_compact_whitespace_trims_mixed_trailing_whitespace_on_last_line_no_newline():
    assert compact_whitespace("abc \t  ") == "abc"

def test_compact_whitespace_trims_trailing_whitespace_on_all_lines():
    text = "line 1  \nline 2\t\nline 3  "
    expected = "line 1\nline 2\nline 3"
    assert compact_whitespace(text) == expected


def test_format_size():
    assert format_size(0) == "0.00 B"
    assert format_size(1023) == "1,023.00 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1536) == "1.50 KB"
    assert format_size(1024 * 1024) == "1.00 MB"
    assert format_size(1024 * 1024 * 1024) == "1.00 GB"
    assert format_size(-1) == "0 B"


def test_format_size_large_values():
    assert format_size(1024**4) == "1.00 TB"
    assert format_size(1024**5) == "1.00 PB"
    assert format_size(1024**6) == "1.00 EB"
    assert format_size(1024**7) == "1.00 ZB"
    assert format_size(1024**8) == "1.00 YB"
    assert format_size(1024**9) == "1,024.00 YB"

def test_utils_tiktoken_import_error_coverage():
    """Cover utils.py lines 12-13: tiktoken ImportError."""
    import runpy
    from unittest.mock import patch
    with patch.dict(sys.modules, {'tiktoken': None}):
        # runpy executes the module in a fresh namespace without reloading it in sys.modules
        utils_namespace = runpy.run_path("utils.py")
        assert 'tiktoken' in utils_namespace

def test_looks_binary_no_args_coverage():
    """Cover utils.py line 179: _looks_binary with no args."""
    from utils import _looks_binary
    assert _looks_binary() is False

def test_parse_time_value_empty_string():
    from utils import parse_time_value
    assert parse_time_value("") == 0.0

def test_parse_time_value_invalid_date_format():
    from utils import parse_time_value
    with pytest.raises(InvalidConfigError) as exc:
        parse_time_value("2024-13-45")
    assert "Invalid date format" in str(exc.value)

@pytest.mark.parametrize("value,expected_delta", [
    ("10s", 10),
    ("2m", 120),
    ("1w", 7 * 24 * 3600),
])
def test_parse_time_value_units(value, expected_delta):
    import time
    from utils import parse_time_value
    val = parse_time_value(value)
    assert time.time() - val == pytest.approx(expected_delta, abs=10)

def test_parse_time_value_unknown_unit_unreachable_branch():
    from unittest.mock import patch, MagicMock
    from utils import parse_time_value
    with patch('re.match') as mock_match:
        mock_m = MagicMock()
        mock_m.group.side_effect = lambda i: "10" if i == 1 else "x"
        mock_match.side_effect = [None, mock_m]
        with pytest.raises(InvalidConfigError) as exc:
            parse_time_value("10x")
        assert "Unknown time unit: 'x'" in str(exc.value)

def test_validate_regex_list_not_a_list():
    with pytest.raises(InvalidConfigError, match="'test' must be a list"):
        _validate_regex_list("not a list", "test", None)

def test_validate_regex_list_item_not_a_dict():
    with pytest.raises(InvalidConfigError, match="Item 0 in 'test' must be a dictionary"):
        _validate_regex_list(["not a dict"], "test", None)

def test_validate_glob_list_not_a_list():
    with pytest.raises(InvalidConfigError, match="'test' must be a list"):
        _validate_glob_list("not a list", "test")

def test_validate_glob_list_none():
    _validate_glob_list(None, "test")

def test_validate_filters_section_not_a_dict():
    config = {"filters": "not a dict"}
    validate_config(config)

def test_validate_processing_section_not_a_dict():
    config = {"processing": "not a dict"}
    validate_config(config)

def test_validate_processing_section_non_bool():
    config = {"processing": {"apply_in_place": "not a bool"}}
    with pytest.raises(InvalidConfigError, match="'processing.apply_in_place' must be true or false"):
        validate_config(config)

    config = {"processing": {"create_backups": "not a bool"}}
    with pytest.raises(InvalidConfigError, match="'processing.create_backups' must be true or false"):
        validate_config(config)

def test_validate_config_missing_nested_key():
    config = {"search": {}}
    nested_required = {"search": ["root_folders"]}
    with pytest.raises(InvalidConfigError, match="'search' section is missing keys: root_folders"):
        validate_config(config, nested_required=nested_required)

def test_process_content_regex_missing_fields():
    text = "hello world"
    options = {
        "regex_replacements": [
            {"pattern": "hello"},
            {"replacement": "bye"},
        ]
    }
    assert process_content(text, options) == text

def test_process_content_compact_whitespace_unknown_key():
    text = "a   b"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "unknown": True,
            "compact_space_runs": True
        }
    }
    assert process_content(text, options) == "a  b"

def test_process_content_compact_whitespace_all_unknown():
    text = "a   b"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "unknown": True
        }
    }
    assert process_content(text, options) == "a  b"

def test_process_content_compact_whitespace_with_none():
    text = "a   b"
    options = {
        "compact_whitespace": True,
        "compact_whitespace_groups": {
            "compact_space_runs": None
        }
    }
    assert process_content(text, options) == "a  b"

def test_validate_glob_pattern_mismatched_brackets(caplog):
    with caplog.at_level(logging.WARNING):
        validate_glob_pattern("file[a-z.txt", context="test")
    assert "mismatched brackets" in caplog.text

def test_validate_compact_whitespace_groups_not_dict(tmp_path):
    """Ensure InvalidConfigError is raised if compact_whitespace_groups is not a dictionary."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace_groups": "not_a_dict"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'processing.compact_whitespace_groups' must be a dictionary"):
        load_and_validate_config(config_path)

def test_validate_compact_whitespace_groups_unknown_key(tmp_path, caplog):
    """Ensure a warning is logged for unknown keys in compact_whitespace_groups."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace_groups": {
                    "unknown_group": True
                }
            }
        }
    )
    with caplog.at_level(logging.WARNING):
        load_and_validate_config(config_path)

    assert "Unknown compact_whitespace_groups entry 'unknown_group'" in caplog.text

def test_validate_compact_whitespace_groups_invalid_value(tmp_path):
    """Ensure InvalidConfigError is raised for non-boolean/non-null values in compact_whitespace_groups."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace_groups": {
                    "spaces_to_tabs": "invalid_value"
                }
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="Values in 'processing.compact_whitespace_groups' must be true, false, or null"):
        load_and_validate_config(config_path)

def test_apply_line_regex_replacements_block_at_eof():
    """Ensure that a matching block at the very end of the string is correctly replaced."""
    text = "line1\nmatch\nmatch"
    rules = [{"pattern": "^match$", "replacement": "replaced"}]

    # The block "match\nmatch" is at the end of the input.
    # The function should detect the end of the block at EOF and append the replacement.
    result = apply_line_regex_replacements(text, rules)
    assert result == "line1\nreplaced"

def test_validate_regex_replacements_invalid_regex(tmp_path):
    """Ensure InvalidConfigError is raised for invalid regex in regex_replacements."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "regex_replacements": [
                    {"pattern": "[invalid_regex", "replacement": "test"}
                ]
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="Invalid regex pattern in processing.regex_replacements\\[0\\]"):
        load_and_validate_config(config_path)

def test_validate_line_regex_replacements_invalid_regex(tmp_path):
    """Ensure InvalidConfigError is raised for invalid regex in line_regex_replacements."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "line_regex_replacements": [
                    {"pattern": "(unclosed group", "replacement": "test"}
                ]
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="Invalid regex pattern in processing.line_regex_replacements\\[0\\]"):
        load_and_validate_config(config_path)

def test_validate_output_format_invalid(tmp_path):
    """Ensure InvalidConfigError is raised for an unsupported output format."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {
                "format": "invalid_format"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'output.format' must be one of: text, json, jsonl, markdown, xml"):
        load_and_validate_config(config_path)

def test_validate_processing_compact_whitespace_non_bool(tmp_path):
    """Ensure InvalidConfigError is raised if processing.compact_whitespace is not a boolean."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "compact_whitespace": "not_a_bool"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'processing.compact_whitespace' must be true or false"):
        load_and_validate_config(config_path)

def test_validate_processing_apply_in_place_non_bool(tmp_path):
    """Ensure InvalidConfigError is raised if processing.apply_in_place is not a boolean."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "processing": {
                "apply_in_place": "not_a_bool"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'processing.apply_in_place' must be true or false"):
        load_and_validate_config(config_path)

def test_validate_output_sort_by_invalid(tmp_path):
    """Ensure InvalidConfigError is raised for an unsupported sort_by value."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {
                "sort_by": "invalid_sort"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'output.sort_by' must be one of: name, size, modified, tokens, depth"):
        load_and_validate_config(config_path)

def test_validate_output_sort_reverse_non_bool(tmp_path):
    """Ensure InvalidConfigError is raised if output.sort_reverse is not a boolean."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "output": {
                "sort_reverse": "not_a_bool"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="'output.sort_reverse' must be true or false"):
        load_and_validate_config(config_path)

def test_validate_filters_max_files_invalid(tmp_path):
    """Ensure InvalidConfigError is raised if filters.max_files is invalid."""
    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {
                "max_files": -1
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="filters.max_files must be 0 or more"):
        load_and_validate_config(config_path)

    config_path = _write_config(
        tmp_path,
        {
            "search": {"root_folders": ["."]},
            "filters": {
                "max_files": "not_an_int"
            }
        }
    )
    with pytest.raises(InvalidConfigError, match="filters.max_files must be 0 or more"):
        load_and_validate_config(config_path)

def test_validate_config_nested_not_dict(tmp_path):
    """Ensure InvalidConfigError is raised if a required nested section is not a dictionary."""
    from utils import validate_config
    config = {"search": "not_a_dict"}
    with pytest.raises(InvalidConfigError, match="'search' section must be a dictionary with keys: root_folders"):
        validate_config(config, nested_required={"search": ["root_folders"]})

def test_validate_config_missing_required_keys():
    config = {"key1": "val1"}
    required_keys = ["key1", "key2"]
    with pytest.raises(InvalidConfigError, match="Config is missing required keys: key2"):
        validate_config(config, required_keys=required_keys)

def test_validate_config_output_not_dict():
    config = {"output": "not_a_dict", "search": {"root_folders": ["."]}}
    validate_config(config)

def test_validate_config_search_not_dict():
    config = {"pairing": {"enabled": True}, "search": None}
    validate_config(config)
    assert isinstance(config["search"], dict)

def test_validate_pairing_section_search_not_dict():
    config = {"pairing": {"enabled": True}, "search": None}
    _validate_pairing_section(config)
    assert isinstance(config["search"], dict)

def test_validate_output_table_of_contents_not_bool():
    config = {
        "output": {"table_of_contents": "not_a_bool"},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="'output.table_of_contents' must be true or false"):
        validate_config(config)

def test_validate_config_deprecated_in_place_groups():
    config = {
        "processing": {"in_place_groups": ["something"]},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="'processing.in_place_groups' is no longer used"):
        validate_config(config)

def test_validate_filters_max_total_tokens_invalid():
    config = {
        "filters": {"max_total_tokens": -1},
        "search": {"root_folders": ["."]}
    }
    with pytest.raises(InvalidConfigError, match="filters.max_total_tokens must be 0 or more"):
        validate_config(config)

def test_validate_filters_search_not_dict():
    config = {
        "filters": {"inclusion_groups": {"test": {"filenames": ["*.py"]}}},
        "search": None
    }
    validate_config(config)
    assert isinstance(config["search"], dict)

def test_load_yaml_config_empty(tmp_path):
    empty_file = tmp_path / "empty.yml"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(InvalidConfigError, match="Configuration file is empty or invalid"):
        load_yaml_config(empty_file)

def test_compact_whitespace_group_none():
    text = "    "
    result = compact_whitespace(text, groups={"spaces_to_tabs": None, "trim_trailing_whitespace": False})
    assert result == "\t"

def test_validate_pairing_section_conflict():
    config = {
        "pairing": {"enabled": True},
        "search": {"root_folders": ["."], "allowed_extensions": [".txt"]}
    }
    with pytest.raises(InvalidConfigError, match="'allowed_extensions' cannot be used when pairing is enabled"):
        validate_config(config)
