# Rainrat TextUtil

This repository contains a simple file-combining utility driven by YAML configuration files.
It can collect source files from multiple directories, apply filtering and text-processing
rules, and output a single consolidated text file or paired files.

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

See `example.yml`, `concat_simple.yml`, and `example_cpp_h.yml` for more configuration
examples.

## Example configurations

- `concat_simple.yml`: basic text file concatenation with minimal options.
- `example.yml`: a full-featured configuration showcasing filtering groups and
  regex-based processing.
- `example_cpp_h.yml`: demonstrates pairing C/C++ source files with their
  corresponding headers.
