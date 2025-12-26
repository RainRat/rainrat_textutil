# SourceCombine

**SourceCombine** is a flexible command-line tool for merging multiple text files into a single output or organized pairs. It uses a YAML configuration file to define rules for file discovery, filtering, and text processing.

Whether you are preparing files for printing, creating context for Large Language Models (LLMs), or simply want a compact archive of your code, SourceCombine streamlines the process.

## Common Use Cases

*   **LLM Context:** Combine your entire project's source code into a single file to provide comprehensive context for AI assistants.
*   **Code Archiving:** Create a snapshot of your source files for documentation or backup purposes.
*   **Code Reviews:** Aggregate dispersed files into one document to easily review or print them.
*   **Preprocessing:** Apply regex replacements or strip comments across multiple files in bulk.
*   **C/C++ Pairing:** Automatically pair source files (`.cpp`) with their headers (`.h`) for organized distribution.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/RainRat/TextUtilities.git
    cd TextUtilities
    ```

2.  **Install Python 3** (version 3.8 or newer).

3.  **Install required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script from the command line, providing a YAML configuration file:

```bash
python sourcecombine.py CONFIG_FILE [--output OUTPUT] [--dry-run] [--verbose] [--clipboard]
```

### Options

*   `--output` / `-o`: Override the output path specified in the configuration.
*   `--dry-run` / `-d`: List matched files and planned outputs without writing any files. Useful for previewing changes.
*   `--verbose` / `-v`: Enable verbose output (DEBUG level) to troubleshoot configuration issues.
*   `--clipboard` / `-c`: Copy the combined output directly to the clipboard instead of writing to a file.
    *   *Note: Clipboard mode is not available when file pairing is enabled.*
*   `--init`: Generate a default configuration file (`sourcecombine.yml`) in the current directory.

### Example

```bash
python sourcecombine.py my_config.yml --dry-run
```

This command will simulate the process defined in `my_config.yml` and show you exactly which files would be included and where they would be written.

## Customizing file boundaries

The `output.header_template` and `output.footer_template` options control the
text written before and after each file's content. The special sequence
`{{FILENAME}}` is replaced with the file's path relative to the configured root
folder.

By default, SourceCombine writes a simple divider around each file:

```yaml
output:
  header_template: "--- {{FILENAME}} ---\n"
  footer_template: "\n--- end {{FILENAME}} ---\n"
```

You can switch back to the older fenced-code-block format by overriding the
templates in your configuration:

```yaml
output:
  header_template: "{{FILENAME}}:\n```\n"
  footer_template: "\n```\n\n"
```

## Global Header and Footer

You can add a custom header at the beginning and a footer at the end of the
entire combined file using `output.global_header_template` and
`output.global_footer_template`. These options are useful for adding license
information, project descriptions, or wrapping the output in a specific format
(like XML or JSON). The templates are written once around the combined output
even when multiple `search.root_folders` are provided, and they also apply when
pairing is enabled (one header and one footer per paired output file).

```yaml
output:
  global_header_template: "# Project Source Code\n\n"
  global_footer_template: "\n# End of Project Source Code\n"
```

## Customizing paired output filenames

When pairing is enabled, you can control the naming of the output files with
the `output.paired_filename_template` option. The template supports the
following placeholders:

- `{{STEM}}`: The base name of the file (e.g., `main` from `main.cpp`).
- `{{SOURCE_EXT}}`: The extension of the source file (e.g., `.cpp`).
- `{{HEADER_EXT}}`: The extension of the header file (e.g., `.h`).
- `{{DIR}}`: The file's relative directory using POSIX separators (or `.` for
  files located directly in the root folder being processed).
- `{{DIR_SLUG}}`: A filesystem-safe version of `{{DIR}}`, lowercased and with
  unsafe characters converted to dashes while preserving the directory
  structure. When `{{DIR}}` is `.`, the slug is `root`.

The default template is `'{{STEM}}.combined'`. You can customize it to match
your project's conventions:

```yaml
output:
  paired_filename_template: '{{STEM}}{{SOURCE_EXT}}.txt'
```

To preserve directory structure when writing paired outputs to a folder, use
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
    - pattern: '^\\s*#\\s*TODO:.*$'
      replacement: ''
```

You can keep only the text between custom markers by using a capture group in
your pattern and referencing it in the replacement string:

```yaml
processing:
  regex_replacements:
    - pattern: '(?s).*BEGIN_SNIP(.*)END_SNIP.*'
      replacement: '\\1'
```

To collapse entire blocks of matching lines, use the `processing.line_regex_replacements`
option. Each rule operates line-by-line: consecutive lines that match the
pattern are removed and optionally replaced with a single `replacement` string.

```yaml
processing:
  line_regex_replacements:
    - pattern: '^\\s*\\w+\(0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+\),\s*$'
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

Exclude entire directories with `filters.exclusions.folders`. Each pattern is
checked against every directory name in the path, so a single entry like
`'build'` will exclude both `./build` and nested folders such as
`./src/app/build`.

When `filters.max_size_bytes` is set to a positive number, files that exceed
the limit are skipped. To leave a marker in the combined output for those
omitted files, set `output.max_size_placeholder` to a string such as
`"[SKIPPED {{FILENAME}}]"`. The `{{FILENAME}}` placeholder is replaced with the
file's path relative to the root folder. The placeholder is written for
oversized files whether pairing is enabled or not; in pairing mode, it replaces
the output for pairs whose primary file exceeds the limit.

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
are treated literally:

```yaml
root_folders:
  - 'C:\Users\Guest\GitHub\myproject'
```

Using double quotes would require escaping each backslash (`"C:\\Users\\Guest"`).

## Example configurations

- `concat_simple.yml`: basic text file concatenation with minimal options.
- `example.yml`: a full-featured configuration showcasing filtering groups and
  regex-based processing.
- `example_cpp_h.yml`: demonstrates pairing C/C++ source files with their
  corresponding headers.
