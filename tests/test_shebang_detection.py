from sourcecombine import find_and_combine_files
from utils import DEFAULT_CONFIG

def test_shebang_detection_markdown_syntax(tmp_path):
    """Verify that an extensionless script with a shebang gets correct Markdown syntax highlighting."""
    # Create an extensionless script with a python shebang
    script_path = tmp_path / "my-python-script"
    script_path.write_text("#!/usr/bin/env python3\nprint('hello')\n", encoding='utf-8')

    config = DEFAULT_CONFIG.copy()
    config['search'] = {'root_folders': [str(tmp_path)]}
    config['output'] = {
        'format': 'markdown',
        # Use a template that uses {{LANG}}
        'header_template': "## {{FILENAME}}\n\n```{{LANG}}\n",
        'footer_template': "\n```\n",
        'file': str(tmp_path / "combined.md")
    }

    find_and_combine_files(config, str(tmp_path / "combined.md"), output_format='markdown')

    combined_content = (tmp_path / "combined.md").read_text()
    assert "```python" in combined_content
    assert "print('hello')" in combined_content

def test_shebang_detection_filtering(tmp_path):
    """Verify that language filtering includes extensionless scripts with a shebang."""
    # Python script
    py_script = tmp_path / "py-script"
    py_script.write_text("#!/usr/bin/python\npass\n", encoding='utf-8')

    # Bash script
    sh_script = tmp_path / "sh-script"
    sh_script.write_text("#!/bin/bash\nls\n", encoding='utf-8')

    config = DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
        'allowed_languages': ['python']
    }
    config['output'] = {'file': str(tmp_path / "combined.txt")}

    stats = find_and_combine_files(config, str(tmp_path / "combined.txt"))

    # Should only include the python script
    assert stats['total_files'] == 1
    combined_content = (tmp_path / "combined.txt").read_text()
    assert "py-script" in combined_content
    assert "sh-script" not in combined_content

def test_shebang_detection_shell_variants(tmp_path):
    """Verify detection of various shell shebangs."""
    sh_script = tmp_path / "script-sh"
    sh_script.write_text("#!/bin/sh\necho 1\n", encoding='utf-8')

    bash_script = tmp_path / "script-bash"
    bash_script.write_text("#!/bin/bash\necho 2\n", encoding='utf-8')

    zsh_script = tmp_path / "script-zsh"
    zsh_script.write_text("#!/usr/bin/zsh\necho 3\n", encoding='utf-8')

    config = DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
        'allowed_languages': ['bash']
    }
    config['output'] = {'file': str(tmp_path / "combined.txt")}

    stats = find_and_combine_files(config, str(tmp_path / "combined.txt"))

    # All three should be identified as 'bash'
    assert stats['total_files'] == 3

def test_shebang_detection_unrecognized_extension(tmp_path):
    """Verify that language filtering includes scripts with shebangs and unrecognized extensions."""
    # Python script with unknown extension
    unknown_script = tmp_path / "script.unknown"
    unknown_script.write_text("#!/usr/bin/python\nprint('hello')\n", encoding='utf-8')

    config = DEFAULT_CONFIG.copy()
    config['search'] = {
        'root_folders': [str(tmp_path)],
        'allowed_languages': ['python']
    }
    config['output'] = {'file': str(tmp_path / "combined.txt")}

    stats = find_and_combine_files(config, str(tmp_path / "combined.txt"))

    # Should include the python script with the unrecognized extension
    assert stats['total_files'] == 1
    combined_content = (tmp_path / "combined.txt").read_text()
    assert "script.unknown" in combined_content
