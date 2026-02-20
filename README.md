# SourceCombine

**SourceCombine** is a tool for your terminal that combines many text files into one file or organized pairs. It uses a YAML configuration file to set rules for finding, filtering, and changing text.

Whether you are preparing files for printing, giving context to AI assistants, or making a small archive of your code, SourceCombine makes it easy.

## Common Use Cases

*   **Context for AI Assistants:** Combine your whole project into one file to give AI assistants better context.
*   **Code Archiving:** Save a snapshot of your source files for documentation or backup.
*   **Code Reviews:** Combine scattered files into one document to review or print them easily.
*   **Preparing Files:** Change text with search-and-replace rules or remove comments from many files at once.
*   **C/C++ Pairing:** Pair source files (`.cpp`) with their headers (`.h`) automatically to keep them organized.
*   **Restoring Code:** Recreate folders and files from combined archives (JSON, XML, Markdown, or Text).

## Installation

1.  **Check your Python version:**
    SourceCombine requires Python 3.10 or newer.
    ```bash
    python --version
    ```

2.  **Get the code:**
    Clone the repository and enter the folder:
    ```bash
    git clone https://github.com/RainRat/TextUtilities.git
    cd TextUtilities
    ```
    *Alternatively, [download the ZIP file](https://github.com/RainRat/TextUtilities/archive/refs/heads/main.zip) and extract it.*

3.  **Set up a virtual environment (Recommended):**
    This keeps the tool's libraries separate from your other Python projects.
    *   **Windows (Command Prompt):**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    *   **Windows (PowerShell):**
        ```bash
        python -m venv venv
        .\venv\Scripts\Activate.ps1
        ```
    *   **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

4.  **Install libraries:**
    Install the necessary software libraries:
    ```bash
    pip install -r requirements.txt
    ```
    *(Optional) For accurate token counting, also install `tiktoken`:*
    ```bash
    pip install tiktoken
    ```

5.  **Verify installation:**
    Check that the tool runs:
    ```bash
    python sourcecombine.py --help
    ```

## Quick Start

The easiest way to use SourceCombine is to run it on a folder.

1.  **Combine files in the current folder:**
    ```bash
    python sourcecombine.py .
    ```
    This combines all files in your current folder into `combined_files.txt`.

2.  **Initialize a configuration file for more control:**
    Generate a starter configuration:
    ```bash
    python sourcecombine.py --init
    ```
    Edit the created `sourcecombine.yml` to set your own rules. Then, simply run the tool:
    ```bash
    python sourcecombine.py
    ```
    *SourceCombine will automatically find and use `sourcecombine.yml` in your current folder.*

## Usage

Run the script from your terminal. You can pass one or more folders, files, or a configuration file.

```bash
python sourcecombine.py [TARGET ...] [OPTIONS]
```

### Options

*   `--output` / `-o`: Override the output path specified in the configuration.
*   `--dry-run` / `-d`: List matched files and planned outputs without writing any files. Useful for previewing changes.
*   `--verbose` / `-v`: Enable verbose output (DEBUG level) to troubleshoot configuration issues.
*   `--clipboard` / `-c`: Copy the combined output directly to your clipboard instead of saving a file.
    *   *Note: You cannot use clipboard mode when file pairing is enabled.*
*   `--format` / `-f`: Choose the output format (`text`, `json`, `markdown`, or `xml`).
    *   *Note: You can also use the shortcuts `-m` (markdown) or `-j` (json). JSON format produces a list of file objects and only works when combining many files into one. Markdown and XML formats automatically use appropriate markers (code blocks for Markdown, tags for XML).*
*   `--line-numbers` / `-n`: Add line numbers to the beginning of each line in the combined output.
*   `--toc` / `-T`: Include a Table of Contents at the beginning of the output file. (Only works when combining many files into one).
*   `--include-tree`: Include a visual folder tree at the start of the output. (Only works when combining many files into one).
*   `--compact` / `-C`: Compact and clean up whitespace in the combined output to save tokens.
*   `--max-tokens`: Stop adding files once this total token limit is reached. (Only works when combining many files into one).
*   `--estimate-tokens` / `-e`: Calculate token counts without creating any files.
    *   *Note: Slower than a regular dry-run because it must read the file contents.*
*   `--list-files` / `-l`: Print a list of files that would be processed to your terminal and exit.
*   `--tree` / `-t`: Show a visual folder tree of all included files and exit.
*   `--files-from`: Read a list of files to process from a text file (or `-` for your terminal). Overrides normal folder scanning.
*   `--extract`: Recreate files and folders from a combined JSON, XML, Markdown, or Text file.
*   `--init`: Generate a default configuration file (`sourcecombine.yml`) in the current folder.
*   `--include` / `-i`: Include only files matching a specific pattern (e.g., `-i "*.py"`). Can be used many times.
*   `--exclude-file` / `-x`: Exclude specific files (e.g., `-x "secret.txt"`). Can be used many times.
*   `--exclude-folder` / `-X`: Exclude specific folders (e.g., `-X "build"`). Can be used many times.

### Examples

**Simulate a run:**
See exactly which files would be included without writing anything:
```bash
python sourcecombine.py my_config.yml --dry-run
```

**Combine files with line numbers:**
Useful for code reviews or providing context to AI assistants:
```bash
python sourcecombine.py src/ --line-numbers
```

**View included files as a tree:**
See the folder structure of all matched files:
```bash
python sourcecombine.py . --tree
```

**Run on a specific folder without a config file:**
Use default settings to combine files in `src/`:
```bash
python sourcecombine.py src/
```

**Combine many folders and files:**
```bash
python sourcecombine.py src/ docs/ README.md
```

**Use a configuration file with override folders:**
```bash
python sourcecombine.py config.yml project_a/ project_b/
```

**Copy output to clipboard:**
Combine files defined in `config.yml` and copy the result:
```bash
python sourcecombine.py config.yml --clipboard
```

**Include only specific file types:**
Combine only Python and Markdown files from the `src/` folder:
```bash
python sourcecombine.py src/ -i "*.py" -i "*.md"
```

**Extract files from a combined archive:**
Recreate your project from a JSON, XML, Markdown, or Text file. You can even
extract directly from your clipboard or your terminal:
```bash
# Extract from a JSON file
python sourcecombine.py --extract combined.json -o restored_project/

# Extract directly from your clipboard
python sourcecombine.py --extract --clipboard -o restored_project/

# Extract from your terminal
cat combined.txt | python sourcecombine.py --extract - -o restored_project/
```

## Table of Contents

For large combined files, you can enable a Table of Contents (TOC) at the top of the output.
This is particularly useful when outputting to Markdown or Text formats.

**CLI:**
```bash
python sourcecombine.py --toc
```

**Configuration:**
```yaml
output:
  table_of_contents: true
```

The Table of Contents lists all included files with their sizes and estimated token counts. In Markdown mode (`--format markdown`), it also creates links to each file section. (This feature only works when combining many files into one).

## Customizing file boundaries

The `output.header_template` and `output.footer_template` options control the
text written before and after each file's content. The following placeholders are
available for these templates:

- `{{FILENAME}}`: The file's path relative to the configured root folder.
- `{{EXT}}`: The file's extension (without the dot).
- `{{STEM}}`: The file name without the extension.
- `{{DIR}}`: The relative folder path using forward slashes.
- `{{DIR_SLUG}}`: A filesystem-safe simplified name for `{{DIR}}` (uses `root` for the project root).
- `{{SIZE}}`: The human-readable size of the file (e.g., `1.20 KB`).
- `{{TOKENS}}`: The estimated number of tokens in the file.
- `{{LINE_COUNT}}`: The number of lines in the file.

By default, SourceCombine writes a simple divider around each file:

```yaml
output:
  header_template: "--- {{FILENAME}} ---\n"
  footer_template: "\n--- end {{FILENAME}} ---\n"
```

You can switch back to the older fenced-code-block format by overriding the
templates in your configuration (Note: SourceCombine automatically uses these
markers when you choose the Markdown or XML output formats):

```yaml
output:
  header_template: "{{FILENAME}}:\n```\n"
  footer_template: "\n```\n\n"
```

## Global Header and Footer

You can add a custom header at the beginning and a footer at the end of the
entire combined file using `output.global_header_template` and
`output.global_footer_template`. These templates are useful for adding license
information, project descriptions, or wrapping the output in a specific format.

When combining many files into one, these templates support metadata placeholders for the
entire project:

- `{{FILE_COUNT}}`: The total number of files included in the output.
- `{{TOTAL_SIZE}}`: The human-readable total size of all included files.
- `{{TOTAL_TOKENS}}`: The total estimated token count.
- `{{TOTAL_LINES}}`: The total line count of all included content.

```yaml
output:
  global_header_template: "# Project: {{FILE_COUNT}} files, {{TOTAL_TOKENS}} tokens\n\n"
  global_footer_template: "\n# End of Project Source Code\n"
```

The templates are written once around the combined output even when many
`search.root_folders` are provided. When pairing is enabled, the global header
and footer are written around each paired output file (though global placeholders
are not supported in pairing mode).

## Customizing paired output filenames

When pairing is enabled, you can control the naming of the output files with
the `output.paired_filename_template` option. The template supports the
following placeholders:

- `{{STEM}}`: The base name of the file (e.g., `main` from `main.cpp`).
- `{{SOURCE_EXT}}`: The extension of the source file (e.g., `.cpp`).
- `{{HEADER_EXT}}`: The extension of the header file (e.g., `.h`).
- `{{DIR}}`: The file's relative folder path using forward slashes (or `.` for
  files located directly in the root folder being processed).
- `{{DIR_SLUG}}`: A filesystem-safe simplified name for `{{DIR}}`, lowercased and
  with unsafe characters converted to dashes while preserving the folder
  structure. When `{{DIR}}` is `.`, the simplified name is `root`.

The default template is `'{{STEM}}.combined'`. You can customize it to match
your project's conventions:

```yaml
output:
  paired_filename_template: '{{STEM}}{{SOURCE_EXT}}.txt'
```

To preserve folder structure when writing paired outputs to a folder, use
the `{{DIR_SLUG}}` placeholder:

```yaml
output:
  folder: './paired'
  paired_filename_template: '{{DIR_SLUG}}/{{STEM}}.combined'
```

## Regex-based text transformations

The `processing.regex_replacements` option lets you apply regular-expression search/replace
rules to each file's content. Each rule specifies a `pattern` and a `replacement`.

```yaml
processing:
  regex_replacements:
    - pattern: '^\s*#\s*TODO:.*$'
      replacement: ''
```

You can keep only the text between custom markers by using a capture group in
your pattern and referencing it in the replacement string:

```yaml
processing:
  regex_replacements:
    - pattern: '(?s).*BEGIN_SNIP(.*)END_SNIP.*'
      replacement: '\1'
```

To combine entire blocks of matching lines, use the `processing.line_regex_replacements`
option. Each rule works line-by-line: lines that follow each other and match the
pattern are removed. They can be replaced with a single `replacement` string.

```yaml
processing:
  line_regex_replacements:
    - pattern: '^\s*\w+\(0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+\),\s*$'
      replacement: '<data removed>'
```

See `example.yml`, `concat_simple.yml`, and `example_cpp_h.yml` for more configuration
examples.

### Applying transformations back to source files

To rewrite the original files with the same transformations used for the
combined output, set `processing.apply_in_place` to `true`. When enabled, the
file is processed and rewritten before it is included in the combined output.
Backups with the `.bak` extension are created by default before any
modification occurs. You can disable the backup behavior by setting
`processing.create_backups` to `false`.

```yaml
processing:
  apply_in_place: true
  create_backups: false  # Optional – defaults to true when apply_in_place is enabled
  compact_whitespace: true
```

In-place updates are skipped automatically when `--dry-run` is used. Previous
configurations that relied on `processing.in_place_groups` are deprecated in
favor of the simpler boolean flag.

### Filtering and Exclusion Rules

Use glob patterns in `filters.exclusions.filenames` to skip specific files.
Patterns can match an extension (`'*.bak'`), a complete filename (`'test.py'`),
or a relative path glob (`'tests/*'`).

Exclude entire folders with `filters.exclusions.folders`. Each pattern is
checked against every folder name in the path, so a single entry like
`'build'` will exclude both `./build` and nested folders such as
`./src/app/build`.

When `filters.max_size_bytes` is set to a positive number, files that exceed
the limit are skipped. To leave a marker in the combined output for those
omitted files, set `output.max_size_placeholder` to a string such as
`"[SKIPPED {{FILENAME}}]"`. The `{{FILENAME}}` placeholder is replaced with the
file's path relative to the root folder. The placeholder is written for
oversized files whether pairing is enabled or not; in pairing mode, it replaces
the output for pairs whose primary file exceeds the limit.

Set `filters.max_total_tokens` to a positive integer to limit the total size of the
combined output document. This is very helpful when preparing context for
AI assistants with specific limits.

Set `filters.skip_binary` to `true` to ignore files that look like binary data
(for example, executables or images) even when they match your other filters.

### Inclusion Groups

Enable selective opt-in filtering by configuring `filters.inclusion_groups`.
Each group defines a set of filename patterns and can be toggled on or off via
its `enabled` flag. When at least one group is enabled, only files matching the
enabled groups' patterns are included in the search results.

### Case-insensitive pattern matching

Filename and folder filters defined in the configuration are matched without
regard to case, so patterns like `src/*` will include `SRC/Example.py` on
case-sensitive filesystems.

### Windows path note

When specifying Windows paths in YAML, wrap them in single quotes so backslashes
are treated exactly as they are:

```yaml
root_folders:
  - 'C:\Users\Guest\GitHub\myproject'
```

Using double quotes would require adding an extra backslash for each one (`"C:\\Users\\Guest"`).

## Example configurations

- `concat_simple.yml`: basic text file concatenation with minimal options.
- `example.yml`: a full-featured configuration showcasing filtering groups and
  regex-based processing.
- `example_cpp_h.yml`: demonstrates pairing C/C++ source files with their
  corresponding headers.

## Troubleshooting

**"Command not found" or "Module not found" errors:**
Ensure you have activated your virtual environment (Step 3 in Installation) and installed the dependencies.

**Permission errors:**
If you see permission errors, check that you have permission to read the files you are trying to combine and permission to write to the output location.

**Encoding issues:**
SourceCombine tries to detect the file encoding, but some files might not work correctly. Try converting them to UTF-8 if you have problems.
