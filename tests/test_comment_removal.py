import pytest
import utils
from pathlib import Path
from sourcecombine import FileProcessor

def test_remove_comments_by_lang_python():
    text = "def hello():\n    # single line\n    print('hi')  # trailing\n    \"\"\" multi\n    line \"\"\"\n    return"
    # Full removal
    processed = utils.remove_comments_by_lang(text, 'python')
    assert "# single line" not in processed
    assert "trailing" not in processed
    assert "multi" not in processed
    assert "return" in processed

    # Single only
    processed = utils.remove_comments_by_lang(text, 'python', single_only=True)
    assert "# single line" not in processed
    assert "multi" in processed

def test_remove_comments_by_lang_cpp():
    text = "// header\n#include <iostream>\n/* multi\n   comment */\nint main() { return 0; } // end"
    processed = utils.remove_comments_by_lang(text, 'cpp')
    assert "// header" not in processed
    assert "multi" not in processed
    assert "// end" not in processed
    assert "#include <iostream>" in processed
    assert "int main()" in processed

def test_process_content_with_comment_removal():
    options = {'remove_comments': True}
    text = "/* comment */\ncode();"
    # Should remove comments when language is provided
    processed = utils.process_content(text, options, language='javascript')
    assert "comment" not in processed
    assert "code();" in processed

    # Should NOT remove comments when language is NOT provided
    processed = utils.process_content(text, options)
    assert "comment" in processed

def test_remove_single_line_comments_only():
    options = {'remove_single_line_comments': True}
    text = "// single\n/* multi */\ncode();"
    processed = utils.process_content(text, options, language='javascript')
    assert "single" not in processed
    assert "/* multi */" in processed

def test_unsupported_language_graceful_fallback():
    text = "?? unknown comment\ncode();"
    processed = utils.remove_comments_by_lang(text, 'unknown-lang')
    assert processed == text

def test_empty_input():
    assert utils.remove_comments_by_lang("", "python") == ""
    assert utils.remove_comments_by_lang(None, "python") is None
