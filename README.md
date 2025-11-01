# RainRat's Text Utilities

Currently this repo contains only SourceCombine, but new tools will be added.

## SourceCombine

A simple file-combining utility driven by YAML configuration files.
It can collect source files from multiple directories, apply filtering and text-processing
rules, and output a single consolidated text file or paired files.

Whether you are preparing files for printing, for providing to an LLM, or just
like all your files you need to refer to presented compactly.

## CLI usage

```bash
python sourcecombine.py CONFIG_FILE [--dry-run]
```

Combine files into one output or pair source and header files into separate
outputs based on the options in `CONFIG_FILE`. Use `--dry-run` to preview the
files and destination paths without writing any output.

When pairing is enabled and `output.folder` is omitted, each resulting
`.combined` file is written alongside its source files. Specify
`output.folder` to collect them in a separate directory.

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

### In-place processing groups

When you want to permanently update the source files themselves—such as
collapsing whitespace before committing them—you can enable
`processing.in_place_groups`. Each named group bundles the same processing
options used for the combined output. When a group is marked as `enabled`, its
options are applied to the file content and the file is rewritten before the
final output is generated.

```yaml
processing:
  in_place_groups:
    cleanup:
      enabled: true
      options:
        compact_whitespace: true
        regex_replacements:
          - pattern: '\\s+$'
            replacement: ''
```

Groups make it easy to toggle related transformations at once rather than
enabling each regex rule individually. In-place processing is skipped when
`--dry-run` is used.

### Filtering and Exclusion Rules

Use glob patterns in `filters.exclusions.filenames` to skip specific files.
Patterns can match an extension (`'*.bak'`), a complete filename (`'test.py'`),
or a relative path glob (`'tests/*'`).

Exclude entire directories with `filters.exclusions.folders`. Each pattern is
checked against every directory name in the path, so a single entry like
`'build'` will exclude both `./build` and nested folders such as
`./src/app/build`.

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
