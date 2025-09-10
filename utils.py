import re
import sys
import yaml


def load_yaml_config(config_file_path):
    """Load a YAML configuration file with basic error handling."""
    print(f"Loading configuration from: {config_file_path}")
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if config is None:
                raise ValueError("Configuration file is empty or invalid.")
            return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at '{config_file_path}'.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


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
    """Remove lines matching a hex pattern, optionally inserting a placeholder once."""
    pattern = re.compile(r"^\s*\w+\(0x[0-9a-fA-F]+,\s*0x[0-9a-fA-F]+\),\s*$")
    lines = text.splitlines()
    out_lines = []
    inserted = False
    for line in lines:
        if pattern.match(line):
            if placeholder and not inserted:
                out_lines.append(placeholder)
                inserted = True
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def load_and_validate_config(config_file_path, required_keys=None, defaults=None, nested_required=None):
    """Load a YAML config file and enforce required keys and defaults."""
    config = load_yaml_config(config_file_path)

    if required_keys:
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            print(f"Error: Config file is missing required keys: {', '.join(missing_keys)}")
            sys.exit(1)

    if defaults:
        for key, value in defaults.items():
            config.setdefault(key, value)

    if nested_required:
        for key, subkeys in nested_required.items():
            if not isinstance(config.get(key), dict):
                print(f"Error: '{key}' section must be a dictionary with keys: {', '.join(subkeys)}")
                sys.exit(1)
            missing_sub = [sub for sub in subkeys if sub not in config[key]]
            if missing_sub:
                print(f"Error: '{key}' section is missing keys: {', '.join(missing_sub)}")
                sys.exit(1)

    return config


def ensure_dict(config, key, defaults=None):
    """Ensure a key exists in config as a dict and apply defaults."""
    if not isinstance(config.get(key), dict):
        config[key] = {}
    if defaults:
        for dkey, dval in defaults.items():
            config[key].setdefault(dkey, dval)
    return config[key]


def remove_c_style_comments(text):
    """Remove all C-style block comments from text."""
    return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)


def process_content(buffer, options):
    """Process text based on a dictionary of options."""
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

    if options.get('snip_pattern'):
        buffer = re.sub(options['snip_pattern'], r'\1', buffer, flags=re.DOTALL)

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
