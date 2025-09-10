# Rainrat TextUtil

This repository contains a simple file-combining utility driven by YAML configuration files.
It can collect source files from multiple directories, apply filtering and text-processing
rules, and output a single consolidated text file or paired files.

## Regex-based text transformations

The `processing.regex_snips` option lets you apply regular-expression search/replace
rules to each file's content. Each rule specifies a `pattern` and a `replacement`.

```yaml
processing:
  regex_snips:
    - pattern: '^\\s*#\\s*TODO:.*$'
      replacement: ''
```

You can also emulate the legacy `snip_pattern` behaviour by using a capture group in
your pattern and referencing it in the replacement string. This allows you to keep only
the text between custom markers:

```yaml
processing:
  regex_snips:
    - pattern: '(?s).*BEGIN_SNIP(.*)END_SNIP.*'
      replacement: '\\1'
```

See `example.yml`, `concat_simple.yml`, and `example_cpp_h.yml` for more configuration
examples.
