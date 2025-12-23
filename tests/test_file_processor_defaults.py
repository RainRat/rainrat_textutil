import io
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.fspath(Path(__file__).resolve().parent.parent))

from sourcecombine import FileProcessor
from utils import DEFAULT_CONFIG

def test_file_processor_uses_default_header_when_missing_in_options(tmp_path):
    """
    Verify that FileProcessor falls back to default header template
    if 'header_template' is missing from output_opts.
    """
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("file content", encoding="utf-8")

    # Empty output options to trigger fallback
    config = {"processing": {}}
    output_opts = {}

    processor = FileProcessor(config, output_opts, dry_run=False)
    output_buffer = io.StringIO()

    processor.process_and_write(file_path, tmp_path, output_buffer)

    result = output_buffer.getvalue()

    default_header_tmpl = DEFAULT_CONFIG['output']['header_template']
    expected_header = default_header_tmpl.replace("{{FILENAME}}", "test_file.txt")

    assert expected_header in result
    assert "file content" in result

def test_file_processor_uses_default_footer_when_missing_in_options(tmp_path):
    """
    Verify that FileProcessor falls back to default footer template
    if 'footer_template' is missing from output_opts.
    """
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("file content", encoding="utf-8")

    config = {"processing": {}}
    output_opts = {}

    processor = FileProcessor(config, output_opts, dry_run=False)
    output_buffer = io.StringIO()

    processor.process_and_write(file_path, tmp_path, output_buffer)

    result = output_buffer.getvalue()

    default_footer_tmpl = DEFAULT_CONFIG['output']['footer_template']
    expected_footer = default_footer_tmpl.replace("{{FILENAME}}", "test_file.txt")

    assert expected_footer in result

def test_file_processor_respects_explicit_none_to_disable_templates(tmp_path):
    """
    Verify that explicit None or empty string in output_opts disables
    header/footer, overriding the default fallback.
    """
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("file content", encoding="utf-8")

    config = {"processing": {}}
    # Explicitly set to None/Empty to disable
    output_opts = {"header_template": None, "footer_template": ""}

    processor = FileProcessor(config, output_opts, dry_run=False)
    output_buffer = io.StringIO()

    processor.process_and_write(file_path, tmp_path, output_buffer)

    result = output_buffer.getvalue()

    # Should not contain defaults
    assert "--- test_file.txt ---" not in result
    assert "--- end test_file.txt ---" not in result
    assert result == "file content"
