import re
import unicodedata
from pathlib import Path

import yaml


DEFAULT_OUTPUT_FILENAME = "combined_files.txt"
FILENAME_PLACEHOLDER = "{{FILENAME}}"

DEFAULT_CONFIG = {
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
        'add_line_numbers': False,
        'header_template': f"--- {FILENAME_PLACEHOLDER} ---\n",
        'footer_template': f"\n--- end {FILENAME_PLACEHOLDER} ---\n",
    },
    'processing': {
        'in_place_groups': {},
    },
}


class ConfigNotFoundError(FileNotFoundError):
    """Raised when the configuration file cannot be found."""


class InvalidConfigError(Exception):
    """Raised when the configuration file is invalid."""


def load_yaml_config(config_file_path):
    """Load a YAML configuration file with basic error handling."""
    print(f"Loading configuration from: {config_file_path}")
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
        raise InvalidConfigError(f"Error parsing YAML file: {e}") from e
    except ValueError as e:
        raise InvalidConfigError(str(e)) from e


def read_file_best_effort(file_path):
    """Attempt to read a file trying several encodings."""

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
        with open(file_path, 'r', encoding='utf-8') as f:
            return _strip_bom(f.read())
    except UnicodeError:
        pass

    try:
        raw_bytes = Path(file_path).read_bytes()
    except Exception:
        print(f"Warning: Could not read {file_path}.")
        return ""

    def _score_text(text):
        score = 0.0
        for ch in text:
            category = unicodedata.category(ch)
            if category.startswith('L'):
                score += 2.0
            elif category.startswith('N'):
                score += 1.5
            elif category.startswith('Z'):
                score += 1.0
            elif category.startswith('P'):
                score += 0.2
            elif category == 'Co':
                score -= 2.0
            elif category.startswith('C'):
                score -= 1.5
        return score

    scored_candidates = []
    candidate_encodings = (
        'utf-16',
        'utf-16-le',
        'utf-16-be',
        'cp1252',
        'latin-1',
    )

    for index, encoding in enumerate(candidate_encodings):
        try:
            decoded = _strip_bom(raw_bytes.decode(encoding))
        except UnicodeError:
            continue
        score = _score_text(decoded)
        normalized = score / max(len(decoded), 1)
        scored_candidates.append((normalized, score, -index, decoded))

    if scored_candidates:
        scored_candidates.sort(reverse=True)
        return scored_candidates[0][3]

    try:
        return _strip_bom(raw_bytes.decode('utf-8', errors='replace'))
    except Exception:
        print(f"Warning: Could not decode {file_path} with any of the attempted encodings.")
        return ""


def compact_whitespace(text):
    """Compact and normalize whitespace within ``text``.

    Transformations are applied in the following order:

    - Normalize Windows (CRLF) and classic Mac (CR) endings to LF.
    - Replace runs of four consecutive spaces with a tab to preserve indentation.
    - Trim spaces that surround tabs so mixed indentation collapses while leaving
      at most a single trailing space when indentation is uneven.
    - Replace mid-line tabs (those not following another tab or a newline) with
      single spaces for readability.
    - Trim trailing horizontal whitespace from lines and collapse multiple blank
      lines into at most two consecutive newlines.
    - Reduce any remaining long runs of spaces to at most two characters.

    Note: keep the regular expressions compatible with Python 3.8 for the sake
    of the packaging targets this project supports.
    """
    # Normalize line endings and replace every four consecutive spaces with a tab.
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r' {4}', '\t', text)
    # Remove spaces around tabs and collapse stray tabs into spaces.
    text = re.sub(r' +\t', '\t', text)
    text = re.sub(r'(?<=[^\n\t])\t +', '\t', text)
    text = re.sub(r'(?<=\n)\t +(?=\S)', '\t', text)
    text = re.sub(r'^\t +(?=\S)', '\t', text)
    text = re.sub(r'\t {2,}(?=\s|$)', '\t ', text)
    text = re.sub(r'(?<=[^\n\t])\t', ' ', text)
    # Strip trailing whitespace and collapse multiple blank lines.
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Reduce runs of spaces to at most two.
    text = re.sub(r' {3,}', '  ', text)
    return text

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

    filters = config.get('filters')
    if isinstance(filters, dict):
        groups = filters.get('inclusion_groups', {})
        if isinstance(groups, dict):
            for group in groups.values():
                if isinstance(group, dict):
                    group.setdefault('enabled', False)
                    group.setdefault('filenames', [])

        if (
            isinstance(groups, dict)
            and any(
                isinstance(g, dict) and g.get('enabled')
                for g in groups.values()
            )
            and config.get('search', {}).get('allowed_extensions')
        ):
            raise InvalidConfigError(
                "'search.allowed_extensions' cannot be used when 'filters.inclusion_groups' are enabled. Please specify file types within the inclusion group patterns (e.g., 'src/**/*.py') or remove 'allowed_extensions'."
            )

    processing_conf = config.get('processing')
    if isinstance(processing_conf, dict):
        in_place_groups = processing_conf.get('in_place_groups', {})
        if isinstance(in_place_groups, dict):
            for group in in_place_groups.values():
                if isinstance(group, dict):
                    group.setdefault('enabled', False)
                    group.setdefault('options', {})

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

    if options.get('compact_whitespace'):
        buffer = compact_whitespace(buffer)

    return buffer


def add_line_numbers(text):
    """Prepend line numbers to each line of text."""
    lines = text.splitlines()
    numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    if text.endswith("\n"):
        numbered.append("")
    return "\n".join(numbered)


def validate_regex_pattern(pattern, *, context="regex pattern"):
    """Return a compiled regex after validating ``pattern``.

    Raises ``InvalidConfigError`` with a helpful message when ``pattern`` is
    invalid. ``context`` describes where the pattern originated so the error
    can guide the user to the right configuration entry.
    """

    try:
        return re.compile(pattern)
    except re.error as exc:
        raise InvalidConfigError(
            f"Invalid regex pattern in {context}: '{pattern}'. {exc}"
        ) from exc

