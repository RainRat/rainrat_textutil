import re
import yaml


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
    encodings = ['utf-8', 'latin-1', 'ascii', 'utf-16']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    print(f"Warning: Could not decode {file_path} with any of the attempted encodings.")
    return ""


def normalize_whitespace(text):
    """Normalize whitespace similarly to previous scripts."""
    previous = None
    while previous != text:
        previous = text
        text = text.replace('    ', '\t').replace('\r', '')
    previous = None
    while previous != text:
        previous = text
        text = text.replace('\t ', '\t').replace(' \n', '\n').replace('\n\n\n', '\n\n').replace('\t\n', '\n')
        text = re.sub(r'(?<!\n|\t)\t', ' ', text)
    return text


def remove_hex_pattern_lines(text, placeholder=None):
    """Remove lines matching a hex pattern.

    Parameters
    ----------
    text : str
        The input text to filter.
    placeholder : str, optional
        If provided, this string is inserted once for each contiguous block
        of removed lines. When ``None``, matching lines are simply deleted.
    """
    pattern = re.compile(r"^\s*\w+\(0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+\),\s*$")
    lines = text.splitlines()
    out_lines = []
    in_block = False
    for line in lines:
        if pattern.match(line):
            in_block = True
            continue
        if in_block and placeholder:
            out_lines.append(placeholder)
            in_block = False
        out_lines.append(line)
    if in_block and placeholder:
        out_lines.append(placeholder)
    return "\n".join(out_lines)


def load_and_validate_config(config_file_path, required_keys=None, defaults=None, nested_required=None):
    """Load a YAML config file and enforce required keys and defaults.

    ``defaults`` may contain nested dictionaries, which are merged recursively
    into the loaded configuration.
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

    return config


def remove_c_style_comments(text):
    """Remove all C-style block comments from text."""
    return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)


def process_content(buffer, options):
    """Process text based on a dictionary of options.

    Supported options include:
    - ``remove_initial_comment`` (bool)
    - ``remove_all_c_style_comments`` (bool)
    - ``regex_snips`` (list of dicts): each rule must contain ``pattern`` (str),
      ``replacement`` (str) and ``enabled`` (bool). To replicate the legacy
      ``snip_pattern`` behaviour, use a rule with your pattern and set
      ``replacement`` to ``"\\1"``.
    - ``normalize_whitespace`` (bool)
    - ``remove_hex_pattern_lines`` (bool or str): if a string is provided, it
      will be used as placeholder text inserted for each contiguous block of
      matching lines that are removed.
    """
    if not options:
        return buffer

    if options.get('remove_initial_comment'):
        stripped = buffer.lstrip()
        if stripped.startswith('/*'):
            end_index = stripped.find('*/', 2)
            if end_index != -1:
                buffer = stripped[end_index + 2:].lstrip()

    if options.get('remove_all_c_style_comments'):
        buffer = remove_c_style_comments(buffer)

    for rule in options.get('regex_snips', []):
        if rule.get('enabled') and 'pattern' in rule and 'replacement' in rule:
            try:
                buffer = re.sub(rule['pattern'], rule['replacement'], buffer)
            except re.error as e:
                print(f"Warning: Invalid regex pattern in config: '{rule['pattern']}'. Error: {e}")

    if options.get('normalize_whitespace'):
        buffer = normalize_whitespace(buffer)

    hex_option = options.get('remove_hex_pattern_lines')
    if hex_option:
        placeholder = hex_option if isinstance(hex_option, str) else None
        buffer = remove_hex_pattern_lines(buffer, placeholder)

    return buffer


def add_line_numbers(text):
    """Prepend line numbers to each line of text."""
    lines = text.splitlines()
    numbered = [f"{i + 1}: {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered)
