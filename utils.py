import logging
import re
from pathlib import Path

from charset_normalizer import from_bytes
import yaml


DEFAULT_OUTPUT_FILENAME = "combined_files.txt"
FILENAME_PLACEHOLDER = "{{FILENAME}}"

COMPACT_WHITESPACE_GROUPS = (
    'normalize_line_endings',
    'spaces_to_tabs',
    'trim_spaces_around_tabs',
    'replace_mid_line_tabs',
    'trim_trailing_whitespace',
    'compact_blank_lines',
    'compact_space_runs',
)

DEFAULT_CONFIG = {
    'logging': {
        'level': 'INFO',
    },
    'filters': {
        'exclusions': {
            'filenames': [],
            'folders': [],
        },
        'inclusion_groups': {},
    },
    'pairing': {
        'enabled': False,
        'source_extensions': [],
        'header_extensions': [],
        'include_mismatched': False,
    },
    'output': {
        'file': DEFAULT_OUTPUT_FILENAME,
        'folder': None,
        'paired_filename_template': '{{STEM}}.combined',
        'add_line_numbers': False,
        'header_template': f"--- {FILENAME_PLACEHOLDER} ---\n",
        'footer_template': f"\n--- end {FILENAME_PLACEHOLDER} ---\n",
        'max_size_placeholder': None,
    },
    'processing': {
        'apply_in_place': False,
        'create_backups': True,
    },
}


class ConfigNotFoundError(FileNotFoundError):
    """Raised when the configuration file cannot be found."""


class InvalidConfigError(Exception):
    """Raised when the configuration file is invalid."""


def load_yaml_config(config_file_path):
    """Load a YAML configuration file with basic error handling."""
    logging.info("Loading configuration from: %s", config_file_path)
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                raise ValueError("Configuration file is empty or invalid.")
            return config
    except FileNotFoundError as e:
        raise ConfigNotFoundError(
            f"Configuration file not found at '{config_file_path}'."
        ) from e
    except yaml.YAMLError as e:
        mark = getattr(e, 'problem_mark', None)
        location = ""
        if mark:
            location = f" at line {mark.line + 1}, column {mark.column + 1}"

        problem = getattr(e, 'problem', None) or str(e)
        context = getattr(e, 'context', None)
        details = f"{context}: {problem}" if context else problem

        hint = None
        if isinstance(e, yaml.scanner.ScannerError) and context:
            if 'quoted scalar' in context:
                hint = "Check for missing closing quotes in your YAML file."

        message = f"Error parsing YAML file{location}: {details}"
        if hint:
            message = f"{message} ({hint})"

        raise InvalidConfigError(message) from e
    except ValueError as e:
        raise InvalidConfigError(str(e)) from e


def read_file_best_effort(file_path):
    """Attempt to read a file trying several encodings.

    The function first attempts UTF-8 with BOM handling, then relies on
    ``charset-normalizer`` to identify a likely encoding before falling back to
    a permissive UTF-8 decode with replacements.
    """

    def _strip_bom(text):
        return text.lstrip('\ufeff')

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return _strip_bom(f.read())
    except UnicodeError:
        pass
    except FileNotFoundError:
        raise

    try:
        raw_bytes = Path(file_path).read_bytes()
    except FileNotFoundError:
        raise
    except Exception:
        logging.warning("Could not read %s.", file_path)
        return ""

    best_guess = from_bytes(raw_bytes).best()
    if best_guess and best_guess.encoding:
        encoding = best_guess.encoding
        if (
            encoding.lower().startswith('utf_16')
            and b'\x00' not in raw_bytes
            and len(raw_bytes) < 6
        ):
            encoding = 'latin-1'
        try:
            return _strip_bom(
                raw_bytes.decode(encoding, errors='replace')
            )
        except LookupError:
            logging.warning(
                "Detected encoding '%s' is not supported.", best_guess.encoding
            )

    logging.warning(
        "Could not detect encoding for %s; decoding with UTF-8 replacements.",
        file_path,
    )
    return _strip_bom(raw_bytes.decode('utf-8', errors='replace'))


def compact_whitespace(text, *, groups=None):
    """Compact and normalize whitespace within ``text``.

    This function is designed for formatting plain text and may not be suitable
    for code, especially Python, where significant whitespace is syntactical.

    Transformations are applied in the following order:

    - Normalize Windows (CRLF) and classic Mac (CR) endings to LF.
    - Convert each run of four consecutive spaces to a tab character. This is
      intended to normalize indentation but may affect other formatting.
    - Trim spaces that surround tabs, which helps collapse mixed indentation.
    - Replace mid-line tabs (those not at the start of a line) with single
      spaces for readability.
    - Trim trailing horizontal whitespace from all lines.
    - Collapse multiple blank lines into at most two consecutive newlines.
    - Reduce any remaining long runs of spaces to at most two characters.

    Note: keep the regular expressions compatible with Python 3.8 for the sake
    of the packaging targets this project supports.
    """
    def _should_apply(key):
        if groups is None:
            return True
        value = groups.get(key, True)
        if value is None:
            return True
        return bool(value)

    if _should_apply('normalize_line_endings'):
        text = text.replace('\r\n', '\n').replace('\r', '\n')
    if _should_apply('spaces_to_tabs'):
        text = re.sub(r' {4}', '\t', text)
    if _should_apply('trim_spaces_around_tabs'):
        text = re.sub(r' +\t', '\t', text)
        text = re.sub(r'(?<=[^\n\t])\t +', '\t', text)
        text = re.sub(r'(?<=\n)\t +(?=\S)', '\t', text)
        text = re.sub(r'^\t +(?=\S)', '\t', text)
        text = re.sub(r'\t {2,}(?=\s|$)', '\t ', text)
    if _should_apply('replace_mid_line_tabs'):
        text = re.sub(r'(?<=[^\n\t])\t', ' ', text)
    if _should_apply('trim_trailing_whitespace'):
        text = re.sub(r'[ \t]+\n', '\n', text)
    if _should_apply('compact_blank_lines'):
        text = re.sub(r'\n{3,}', '\n\n', text)
    if _should_apply('compact_space_runs'):
        text = re.sub(r' {3,}', '  ', text)
    return text


def _validate_compact_whitespace_groups(groups, *, context):
    if groups is None:
        return
    if not isinstance(groups, dict):
        raise InvalidConfigError(
            f"'{context}' must be a dictionary mapping group names to booleans or null."
        )

    for key, value in groups.items():
        if key not in COMPACT_WHITESPACE_GROUPS:
            logging.warning(
                "Unknown compact_whitespace_groups entry '%s' in %s; it will be ignored.",
                key,
                context,
            )
            continue
        if value is not None and not isinstance(value, bool):
            raise InvalidConfigError(
                f"Values in '{context}' must be true, false, or null."
            )

def _replace_line_block(text, regex, replacement=None):
    """Collapse blocks of lines matching ``regex`` into ``replacement``.

    ``regex`` should be a compiled regular expression that matches an entire
    line. Consecutive matching lines are treated as a single block. If
    ``replacement`` is ``None`` the block is simply removed; otherwise
    ``replacement`` is inserted once for each block.
    """
    lines = text.splitlines()
    out_lines = []
    in_block = False
    for line in lines:
        if regex.match(line):
            in_block = True
            continue
        if in_block:
            if replacement is not None:
                out_lines.append(replacement)
            in_block = False
        out_lines.append(line)
    if in_block:
        if replacement is not None:
            out_lines.append(replacement)
    return "\n".join(out_lines)


def _validate_filters_section(config):
    """Validate the 'filters' section of the configuration."""
    filters = config.get('filters')
    if not isinstance(filters, dict):
        return

    exclusions_conf = filters.get('exclusions', {})
    if isinstance(exclusions_conf, dict):
        filenames = exclusions_conf.get('filenames', [])
        if isinstance(filenames, list):
            for i, pattern in enumerate(filenames):
                sanitized = validate_glob_pattern(
                    pattern, context=f"filters.exclusions.filenames[{i}]"
                )
                if sanitized != pattern:
                    filenames[i] = sanitized

    groups = filters.get('inclusion_groups', {})
    if isinstance(groups, dict):
        for group_name, group in groups.items():
            if isinstance(group, dict):
                group.setdefault('enabled', False)
                group.setdefault('filenames', [])
                filenames = group.get('filenames', [])
                if isinstance(filenames, list):
                    for i, pattern in enumerate(filenames):
                        sanitized = validate_glob_pattern(
                            pattern,
                            context=f"filters.inclusion_groups.{group_name}.filenames[{i}]",
                        )
                        if sanitized != pattern:
                            filenames[i] = sanitized

    search_conf = config.get('search')
    if not isinstance(search_conf, dict):
        search_conf = {}
        config['search'] = search_conf

    if (
        isinstance(groups, dict)
        and any(
            isinstance(g, dict) and g.get('enabled') for g in groups.values()
        )
        and config.get('search', {}).get('allowed_extensions')
    ):
        raise InvalidConfigError(
            "'filters.inclusion_groups' and 'search.allowed_extensions' are mutually exclusive; "
            "specify file types in your inclusion group patterns instead (e.g., 'src/**/*.py')."
        )


def _validate_processing_section(config, *, source=None):
    """Validate the 'processing' section of the configuration."""
    processing_conf = config.get('processing')
    if not isinstance(processing_conf, dict):
        return

    apply_in_place = processing_conf.get('apply_in_place')
    if apply_in_place is not None and not isinstance(apply_in_place, bool):
        raise InvalidConfigError(
            "'processing.apply_in_place' must be a boolean value"
        )

    create_backups = processing_conf.get('create_backups')
    if create_backups is not None and not isinstance(create_backups, bool):
        raise InvalidConfigError(
            "'processing.create_backups' must be a boolean value"
        )

    _validate_compact_whitespace_groups(
        processing_conf.get('compact_whitespace_groups'),
        context='processing.compact_whitespace_groups',
    )

    # Validate regex patterns in regex_replacements
    regex_replacements = processing_conf.get('regex_replacements', [])
    if isinstance(regex_replacements, list):
        for i, rule in enumerate(regex_replacements):
            if isinstance(rule, dict) and 'pattern' in rule:
                validate_regex_pattern(
                    rule['pattern'],
                    context=f"processing.regex_replacements[{i}]",
                    source=source,
                )

    # Validate regex patterns in line_regex_replacements
    line_regex_replacements = processing_conf.get('line_regex_replacements', [])
    if isinstance(line_regex_replacements, list):
        for i, rule in enumerate(line_regex_replacements):
            if isinstance(rule, dict) and 'pattern' in rule:
                validate_regex_pattern(
                    rule['pattern'],
                    context=f"processing.line_regex_replacements[{i}]",
                    source=source,
                )

    if 'in_place_groups' in processing_conf:
        raise InvalidConfigError(
            "'processing.in_place_groups' has been deprecated. "
            "Use 'processing.apply_in_place' instead."
        )


def _validate_pairing_section(config):
    """Validate the 'pairing' section and its interaction with 'search'."""
    pairing_conf = config.get('pairing', {}) or {}
    search_conf = config.get('search')
    if not isinstance(search_conf, dict):
        search_conf = {}
    config['search'] = search_conf

    if pairing_conf.get('enabled'):
        if search_conf.get('allowed_extensions'):
            raise InvalidConfigError(
                "'allowed_extensions' cannot be used when pairing is enabled; remove it or disable pairing."
            )
        source_exts = tuple(
            e.lower() for e in (pairing_conf.get('source_extensions') or [])
        )
        header_exts = tuple(
            e.lower() for e in (pairing_conf.get('header_extensions') or [])
        )
        effective_allowed_extensions = source_exts + header_exts
    else:
        effective_allowed_extensions = tuple(
            e.lower() for e in (search_conf.get('allowed_extensions') or [])
        )

    search_conf['effective_allowed_extensions'] = effective_allowed_extensions


def _validate_output_section(config):
    """Validate the 'output' section of the configuration."""

    output_conf = config.get('output')
    if not isinstance(output_conf, dict):
        return

    placeholder = output_conf.get('max_size_placeholder')
    if placeholder is not None and not isinstance(placeholder, str):
        raise InvalidConfigError(
            "'output.max_size_placeholder' must be a string or null."
        )


def apply_line_regex_replacements(text, rules):
    """Apply line-oriented regex replacements.

    Each rule in ``rules`` must provide a ``pattern`` key. If ``replacement``
    is supplied, it is inserted once for each contiguous block of matching
    lines; otherwise matching lines are removed. Rules are applied
    sequentially.
    """
    for rule in rules or []:
        pattern = rule.get('pattern')
        if not pattern:
            continue
        replacement = rule.get('replacement')
        compiled = validate_regex_pattern(
            pattern, context="processing.line_regex_replacements"
        )
        text = _replace_line_block(text, compiled, replacement)
    return text


def load_and_validate_config(
    config_file_path,
    required_keys=None,
    defaults=DEFAULT_CONFIG,
    nested_required=None,
):
    """Load a YAML config file and enforce required keys and defaults.

    ``defaults`` may contain nested dictionaries, which are merged recursively
    into the loaded configuration. The canonical defaults are provided by
    ``DEFAULT_CONFIG`` but may be overridden or extended via the ``defaults``
    parameter.
    """
    config = load_yaml_config(config_file_path)

    if required_keys:
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise InvalidConfigError(
                f"Config file is missing required keys: {', '.join(missing_keys)}"
            )

    if defaults:
        def apply_defaults(cfg, defs):
            for key, value in defs.items():
                if isinstance(value, dict):
                    node = cfg.setdefault(key, {})
                    if isinstance(node, dict):
                        apply_defaults(node, value)
                else:
                    cfg.setdefault(key, value)

        apply_defaults(config, defaults)

    if nested_required:
        for key, subkeys in nested_required.items():
            if not isinstance(config.get(key), dict):
                raise InvalidConfigError(
                    f"'{key}' section must be a dictionary with keys: {', '.join(subkeys)}"
                )
            missing_sub = [sub for sub in subkeys if sub not in config[key]]
            if missing_sub:
                raise InvalidConfigError(
                    f"'{key}' section is missing keys: {', '.join(missing_sub)}"
                )

    _validate_filters_section(config)
    _validate_processing_section(config, source=config_file_path)
    _validate_pairing_section(config)
    _validate_output_section(config)

    return config


def process_content(buffer, options):
    """Process text based on a dictionary of options.

    Supported options include:
    - ``remove_initial_c_style_comment`` (bool)
    - ``remove_all_c_style_comments`` (bool)
    - ``regex_replacements`` (list of dicts): each rule must contain ``pattern`` (str)
      and ``replacement`` (str). Rules are applied sequentially. Capture groups
      can be referenced in the replacement string (e.g., ``"\\1"``).
    - ``line_regex_replacements`` (list of dicts): like ``regex_replacements`` but
      applied to whole lines. Consecutive blocks of matching lines collapse into a
      single ``replacement`` entry (or are removed if ``replacement`` is omitted).
    - ``compact_whitespace`` (bool)
    - ``compact_whitespace_groups`` (dict): optional overrides that enable or disable
      specific whitespace transformations. Supported keys are defined in
      ``COMPACT_WHITESPACE_GROUPS``.
    """
    if not options:
        return buffer

    if options.get('remove_initial_c_style_comment'):
        stripped = buffer.lstrip()
        if stripped.startswith('/*'):
            end_index = stripped.find('*/', 2)
            if end_index != -1:
                buffer = stripped[end_index + 2:].lstrip()

    if options.get('remove_all_c_style_comments'):
        buffer = re.sub(r'/\*.*?\*/', '', buffer, flags=re.DOTALL)

    regex_rules = []
    for rule in options.get('regex_replacements', []):
        pattern = rule.get('pattern')
        replacement = rule.get('replacement')
        if pattern is None or replacement is None:
            continue
        compiled = validate_regex_pattern(
            pattern, context="processing.regex_replacements"
        )
        regex_rules.append((compiled, replacement))

    for compiled, replacement in regex_rules:
        buffer = compiled.sub(replacement, buffer)

    line_rules = options.get('line_regex_replacements')
    if line_rules:
        buffer = apply_line_regex_replacements(buffer, line_rules)

    compact_enabled = bool(options.get('compact_whitespace'))
    compact_overrides = options.get('compact_whitespace_groups')
    resolved_groups = None

    if isinstance(compact_overrides, dict):
        resolved_groups = {key: compact_enabled for key in COMPACT_WHITESPACE_GROUPS}
        recognized_override_present = False

        for key, value in compact_overrides.items():
            if key not in resolved_groups:
                continue
            recognized_override_present = True
            if value is None:
                continue
            resolved_groups[key] = bool(value)

        if recognized_override_present:
            compact_enabled = any(resolved_groups.values())
        else:
            resolved_groups = None

    if compact_enabled:
        buffer = compact_whitespace(buffer, groups=resolved_groups)

    return buffer


def add_line_numbers(text):
    """Prepend line numbers to each line of text."""
    lines = text.splitlines()
    numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    if text.endswith("\n"):
        numbered.append("")
    return "\n".join(numbered)


def validate_glob_pattern(pattern, *, context="glob pattern"):
    """Warn about potentially problematic glob patterns."""
    if not isinstance(pattern, str):
        raise InvalidConfigError(
            f"Glob pattern in {context} must be a string, but got: {type(pattern).__name__}"
        )

    normalized = pattern
    if '\\' in pattern:
        normalized = pattern.replace('\\', '/')
        normalized = re.sub(r'/+', '/', normalized)
        logging.warning(
            "Glob pattern in %s ('%s') uses backslashes; treating them as '/' for cross-platform matching.",
            context,
            pattern,
        )

    if normalized.startswith('/') or (len(normalized) > 1 and normalized[1] == ':'):
        logging.warning(
            "Glob pattern in %s ('%s') looks like an absolute path. "
            "Patterns are matched against relative paths and filenames. This may not work as expected.",
            context,
            pattern,
        )

    if '(' in normalized or ')' in normalized or '+' in normalized:
        logging.warning(
            "Glob pattern in %s ('%s') contains characters that may be "
            "interpreted as regular expression syntax, but this tool uses glob patterns. "
            "Special glob characters are *, ?, [].",
            context,
            pattern,
        )

    if normalized.count('[') != normalized.count(']'):
        logging.warning(
            "Glob pattern in %s ('%s') has mismatched brackets '[' and ']'. "
            "This may cause unexpected matching behavior.",
            context,
            pattern,
        )

    return normalized


def validate_regex_pattern(pattern, *, context="regex pattern", source=None):
    """Return a compiled regex after validating ``pattern``.

    Raises ``InvalidConfigError`` with a helpful message when ``pattern`` is
    invalid. ``context`` describes where the pattern originated so the error
    can guide the user to the right configuration entry.
    """

    try:
        return re.compile(pattern)
    except re.error as exc:
        location = f"Invalid regex pattern in {context}"
        if source:
            location += f" (from '{source}')"
        raise InvalidConfigError(
            f"{location}: '{pattern}'. {exc}"
        ) from exc

